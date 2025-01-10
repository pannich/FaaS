from task_dispatcher import TaskDispatcher
import zmq
from utils import serialize, deserialize
from message import Message
import time 
from collections import defaultdict
from threading import Lock,Thread
import config 

class PushTaskDispatcher(TaskDispatcher):
    def __init__(self, port):
        super().__init__()

        # ID for the dispatcher  
        self.dispatcher_id = "PUSH_DISPATCHER"

        # Socket set-up
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.setsockopt_string(zmq.IDENTITY, self.dispatcher_id)
        self.socket.bind(f'tcp://127.0.0.1:{port}')

        # Flag to check if dispatcher is running
        self.running = True 

        # Create a Pub/Sub object for subscribing to channels and 
        # handling messages in the Redis Pub/Sub messaging system.
        self.pubsub = self.redis_client.pubsub()

        # Track workers load in the dispatcher
        # This is also a way to track all the available reg workers 
        # worker_id --> {load:int, active_tasks: set(), last_heartbeat: timestamp}
        self.workers_load = defaultdict(lambda: {"load": 0, "active_tasks": set()})

        # worker_id --> last_heartbeat 
        self.workers_heartbeat = {}

        # A lock to ensure consistency when changing workers_load 
        self.lock = Lock()

        # Debug message
        print(f"Started push task dispatcher on port {port}")

        self.heartbeat_thread = None 
        self.check_heartbeats()

    def initiate_dispatch(self):
        """
        Subscribes to and checks if any new tasks are present 
        on a "tasks" channel. Pushes tasks onto worker. 
        Also routes messages from DEALER (worker) based
        on type of message sent.
        """
        try:
            self.pubsub.subscribe('tasks')
            print("Subscribed to 'tasks' channel. Waiting for messages...")
            print(" ")
        except Exception as e:
            print(f"Error while subscribing to 'tasks' channel {e}")

        try: 
            while self.running:
                # Listen to messages from DEALERS
                # This will be serialized Message object
                try: 
                    worker_id, _, ser_worker_message = self.socket.recv_multipart(flags=zmq.NOBLOCK)
                    worker_id = worker_id.decode()
                    ser_worker_message = ser_worker_message.decode()
                    
                    if ser_worker_message:
                        # Deserialize into a Message object 
                        worker_message = deserialize(ser_worker_message)
                        if not isinstance(worker_message, Message):
                            print("Message received by push dispatcher is not of Message Class type")
                            continue
                        print("[MESSAGE RECEIVED]", worker_message)

                        # CASE 1: New worker is registering 
                        if worker_message.msg_type == Message.Type.WORKER_REGISTRATION:
                            self.handle_registration(worker_id)

                        # CASE 2: Worker indicated task completed
                        elif (worker_message.msg_type == Message.Type.TASK_COMPLETED) and (worker_id in self.workers_load):
                            # Task result will be in its serialized format 
                            self.handle_task_completed(worker_id, worker_message.task_id, worker_message.ser_task_result)
                        
                        # CASE 3: Worker indicated task failed 
                        elif (worker_message.msg_type == Message.Type.TASK_FAILED) and (worker_id in self.workers_load):
                            # Task result will contain error info in its serialized format
                            self.handle_task_failed(worker_id, worker_message.task_id, worker_message.ser_task_result)
                        
                        # CASE 4: Worker sends heartbeat
                        elif (worker_message.msg_type == Message.Type.HEARTBEAT) and (worker_id in self.workers_load):
                            # Task result will contain error info in its serialized format
                            self.update_heartbeats(worker_id)
                        
                        # DEFAULT CASE 
                        else:
                            pass 
                except zmq.Again:
                    # No messages from workers, continue
                    pass
                except zmq.error.ZMQError as e:
                    print(f"ZMQ error: {e}")
                    if e.errno == zmq.ETERM:
                        break
                except Exception as e:
                    print("Error receiving messages from push workers")

                # Send Messages
                try: 
                    # Once we have workers, we can pull messages from channel
                    if len(self.workers_load) < 1:
                        continue 
                    
                    # Check channel for tasks 
                    message = self.pubsub.get_message(timeout=1)

                    # Filter for actual messages
                    # This avoids processing non-message events.
                    task_id = None 
                    if message and message["type"] == "message":
                        # Should receive task_id (str)
                        task_id = message.get('data')

                        if task_id:
                            print(f"[TASK RECEIVED] Received task from Redis task channel: {task_id}")
                            self.handle_task(self.dispatcher_id, task_id)
                except Exception as e:
                    error_message = ("Error sending messages to push workers")
                    TaskDispatcher.handle_task_failure(self.dispatcher_id, task_id, error_message) if task_id else None

        except KeyboardInterrupt:
            print("KeyboardInterrupt received. Shutting down...")
            self.shutdown()
        except Exception as e:
            print(f"Error processing messages {e}")
    
    def handle_registration(self, worker_id):
        """
        Registers a new worker into the PushTaskDispatcher
        """
        try:
            # Register the worker 
            with self.lock:
                if worker_id not in self.workers_load:
                    # Initialize a set that will hold running task_ids
                    self.workers_load[worker_id]["load"] = 0 
                    self.workers_load[worker_id]["active_tasks"] = set() 
                    self.workers_heartbeat[worker_id] = time.time()
            
            # Send an acknowledgement to let worker knwo registration was successful
            msg = Message(Message.Type.ACK, worker_id)
            ser_msg = serialize(msg)
            self.socket.send_multipart([worker_id.encode(), b"", ser_msg.encode()])
            print(f"[WORKER REGISTERED] Registered worker {worker_id}")

        except Exception as e:
            print(f"Error registering worker {e}")
            return 
        
    def load_balance(self):
        """
        Return the worker_id with the minimum load based on self.workers_load[worker_id]["load"]
        """
        with self.lock:
            return min(self.workers_load, key=lambda worker_id: self.workers_load[worker_id]["load"])
    
    def handle_task(self, worker_id, task_id: str):
        """
        Responsible for constructing a task from 
        task_id and sending serialized message
        with task information to the worker 
        with minimum tasks.
        """
        if len(self.workers_load) == 0:
            return
        
        # Check which worker has minimum tasks assigned to it 
        min_load_worker_id = self.load_balance()

        # Get task details from Redis 
        try:
            ser_func_body, ser_func_args = TaskDispatcher.fetch_task_data(task_id)
        except Exception as e:
            error_message = f"Error fetching task data for {task_id}"
            TaskDispatcher.handle_task_failure(min_load_worker_id, task_id, error_message)
            return 

        # Construct NEW_REDIS_TASK message
        try:            
            # Serialize the msg object
            msg = Message(Message.Type.NEW_REDIS_TASK, 
                    min_load_worker_id, 
                    ser_func_body = ser_func_body, 
                    ser_func_args = ser_func_args,
                    task_id = task_id,) 
            
            ser_msg = serialize(msg)
            self.socket.send_multipart([min_load_worker_id.encode(), b"", ser_msg.encode()])
        except Exception as e:
            error_message = f"Error sending task to a worker {e}"
            TaskDispatcher.handle_task_failure(worker_id, task_id, error_message)
            return
        
        try:
            with self.lock:
                # Update load of worker upon sending
                self.workers_load[min_load_worker_id]["load"] += 1 
                self.workers_load[min_load_worker_id]["active_tasks"].add(task_id)
        except Exception as e:
            error_message = f"Error increasing worker load {e}"
            return
        
        try:
            # Set status of task to "RUNNING"
            TaskDispatcher.update_task_status(task_id, TaskDispatcher.STATUS.RUNNING)
            print(f"[TASK DISPATCHED] Task {task_id} sent to worker {min_load_worker_id} and status:RUNNING")
        except Exception as e:
            error_message = f"Error updating task status to running: {e}"
            return
             
    def handle_task_completed(self, worker_id, task_id, ser_task_result):
        """
        Updates task result in redis upon receiving 
        an update from a push worker that task completed. 
        """
        try:
            self.reduce_worker_load(worker_id, task_id)
        except Exception as e:
            error_message = f"Error reducing work load for COMPLETED:{e}"
            print(error_message)

        try:
            # Update redis with result
            TaskDispatcher.update_task_result(task_id, ser_task_result)

            # Update status as complete 
            TaskDispatcher.update_task_status(task_id, TaskDispatcher.STATUS.COMPLETED)
        except Exception as e:
            error_message = f"Error updating COMPLETED task result and status:{e}"
            TaskDispatcher.handle_task_failure(worker_id, task_id, error_message)
            return 
  
    def handle_task_failed(self, worker_id, task_id, ser_task_result):
        """
        Updates task status in redis upon receiving 
        an update from a push worker 
        that task has completed running unsuccessfully
        """
        try:
            self.reduce_worker_load(worker_id, task_id)
        except Exception as e:
            error_message = f"Error reducing work load for COMPLETED:{e}"
            print(error_message)

        try:
            # Update redis with result
            # Result now contains info about error that occured 
            # When worker was processing function 
            TaskDispatcher.update_task_result(task_id, ser_task_result)

            # Update REDIS state 
            TaskDispatcher.update_task_status(task_id, TaskDispatcher.STATUS.FAILED) 
        
        except Exception as e:
            error_message = f"Error updating FAILED task result and status::{e}"
            TaskDispatcher.handle_task_failure(worker_id, task_id, error_message)
            return 
         
    def reduce_worker_load(self, worker_id, task_id):
        """
        Removes active task from self.active_tasks when 
        task runs and enters 
        COMPLETED or FAILED state
        """
        with self.lock:
            try:
                # Remove the key and handle if it doesn't exist
                if worker_id in self.workers_load and self.workers_load[worker_id]["load"] > 0:
                    self.workers_load[worker_id]["active_tasks"].remove(task_id)
                return
            except Exception as e:
                print(f"Error while reducing work load for worker {worker_id}: {e}")

    def update_heartbeats(self, worker_id):
        """
        Updates the heartbeats of workers upon
        receiving a heartbeat from them.
        """
        if worker_id in self.workers_load:
            self.workers_heartbeat[worker_id]= time.time()
        return 

    def check_heartbeats(self):
        """
        Periodically checks for unresponsive workers.
        If the dispatcher detects that a worker hasn't sent a 
        heartbeat within a predefined interval, it marks the 
        worker as unresponsive.
        """
        print("Running heartbeat checks for fault tolerance")

        def monitor_heartbeats():
            while True:
                # Logic for checking the heartbeats
                for worker_id in list(self.workers_heartbeat.keys()):
                    if time.time() - self.workers_heartbeat[worker_id] > config.HEARTBEAT_TIMEOUT:
                        dead_worker_id = worker_id
                        print(f"[WORKER FAILURE DETECTED] Worker {dead_worker_id} failed (missed heartbeat)")
                        with self.lock:
                            dead_worker_data = self.workers_load.pop(dead_worker_id, None)
                        
                        self.workers_heartbeat.pop(dead_worker_id, None)
                        # Send a worker failure message for each of these 
                        for task_id in dead_worker_data["active_tasks"]:
                            error_message = f"Worker {dead_worker_id} running {task_id} failed (missed heartbeat)"
                            TaskDispatcher.handle_worker_failure(dead_worker_id, task_id, error_message)

                time.sleep(config.HEARTBEAT_INTERVAL)

        self.heartbeat_thread = Thread(target=monitor_heartbeats, daemon=True)
        self.heartbeat_thread.start()

    def shutdown(self):
        """
        Gracefully shuts down Push task dispatcher
        """
        try:
            print("Shutting down push task dispatcher")

            # Set running flag to False
            self.running = False

            # Stop the heartbeat thread
            self.heartbeat_thread.join(timeout=1)

            # Close pubsub connection
            self.pubsub.close()

            # Close ZeroMQ socket
            self.socket.close()

            # Terminate ZeroMQ context
            self.context.term()

            # Close Redis client
            TaskDispatcher.redis_client.close()

            print("Push task dispatcher shutdown.")
        except Exception as e:
            print("Error while shutting down push dispatcher")


