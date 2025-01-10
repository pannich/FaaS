from task_dispatcher import TaskDispatcher
import zmq
from utils import deserialize, serialize
from message import Message
import threading
import time 
from collections import defaultdict
import config

class PullTaskDispatcher(TaskDispatcher):
    def __init__(self, port, task_timeout=config.TASK_DEADLINE):
        super().__init__()

        # ID for the dispatcher  
        self.dispatcher_id = "PULL_DISPATCHER"

        # Set up a REP socket to listen to REQ at port given 
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f'tcp://127.0.0.1:{port}')

        # Maintain registered worker info in a set 
        # This will ensure only registered workers communicate
        self.reg_workers = set()

        # Flag tracks if REP sent 
        # Ensures REQ -> REP alternation is maintained
        self.replied = False 

        # Debug message
        self.running = True 
        print(f"Started pull task dispatcher on port {port}")

        # Task timeout check for workers 
        # "task_id" -> ["worker_id", "deadline"]
        self.active_tasks = defaultdict(list) 

        # Start the health-checker thread
        self.task_timeout = task_timeout 
        self.checker_thread = None 
        self.check_task_timeout()

    def initiate_dispatch(self):
        """
        Upon receiving a REQ, checks Redis to see
        if any new tasks are present on a task-queue. 
        """

        try: 
            while self.running:
                # Wait for a worker to request a task
                # This will be serialized Message object 
                ser_worker_message = self.socket.recv_string()
                
                if ser_worker_message:
                    # Deserialize into a Message object 
                    worker_message = deserialize(ser_worker_message)
                    if not isinstance(worker_message, Message):
                        print("Message received by pull dispatcher is not of Message Class type")
                        continue
                    self.replied = False 
                    print("[MESSAGE RECEIVED]", worker_message)

                # CASE 1: New worker is registering 
                if worker_message.msg_type == Message.Type.WORKER_REGISTRATION:
                    self.handle_registration(worker_message.worker_id)

                # CASE 2: If worker is requesting a task 
                elif worker_message.msg_type == Message.Type.WORKER_TASK_REQUEST\
                    and worker_message.worker_id in self.reg_workers:
                    # Fetch a task 
                    task_id = TaskDispatcher.redis_client.lpop("task_queue")

                    if task_id == None:
                        self.handle_no_task(worker_message.worker_id)
                        continue
                    else:
                        # There is a task to be processed 
                        print(f"[TASK RECEIVED] Received task from Redis task queue: {task_id}")
                        self.handle_task(worker_message.worker_id, task_id)

                # CASE 3: Worker indicated task completed
                elif worker_message.msg_type == Message.Type.TASK_COMPLETED\
                    and worker_message.worker_id in self.reg_workers:
                    # Task result will be in its serialized format 
                    self.handle_task_completed(worker_message.worker_id, worker_message.task_id, worker_message.ser_task_result)
                
                # CASE 4: Worker indicated task failed 
                elif worker_message.msg_type == Message.Type.TASK_FAILED\
                    and worker_message.worker_id in self.reg_workers:
                    # Task result will contain error info in its serialized format
                    self.handle_task_failed(worker_message.worker_id, worker_message.task_id, worker_message.ser_task_result)
                
                # DEFAULT CASE 
                else:
                    print(f"Incorrect Message Type sent to Dispatcher {worker_message.msg_type}")
                    self.notify_error(worker_message.worker_id)
        except KeyboardInterrupt:
            print("KeyboardInterrupt received. Shutting down...")
            self.shutdown()
        except Exception as e:
            print(f"Error processing message {e}")
            self.notify_error(worker_message.worker_id)     

    def handle_registration(self, worker_id):
        """
        Registers a new worker into the 
        PullTaskDispatcher and sends an 
        ACK to worker. 
        """
        try:
            # Register 
            if worker_id not in self.reg_workers:
                # Initialize a set that will hold running task_ids
                self.reg_workers.add(worker_id)
            
            # Send message 
            msg = Message(Message.Type.ACK, worker_id)
            ser_msg = serialize(msg)

            self.socket.send_string(ser_msg)
            self.replied = True 
            print(f"[WORKER REGISTERED] Registered worker {worker_id}")
        except Exception as e:
            print(f"Error registering worker {e}")
            self.notify_error(worker_id)
            return 

    def handle_no_task(self, worker_id:str):
        """
        Informs the worker that there are no tasks
        currently available for processing.
        """
        msg = Message(Message.Type.NO_REMAINING_TASKS,
                      worker_id)

        try:
            # Serialize the msg object 
            ser_msg = serialize(msg)

            # Send it to the requesting worker
            self.socket.send_string(ser_msg) 
            self.replied = True 
        except Exception as e:
            print(f"Error sending NO_TASK message to a worker {e}")
            self.notify_error(worker_id)
            return 
        
    def handle_task(self, worker_id: str, task_id: str):
        """
        Responsible for constructing a task from 
        task_id and sending serialized message
        with task information to the worker 
        requesting a task.
        """
        try:
            ser_func_body, ser_func_args = TaskDispatcher.fetch_task_data(task_id)
        except Exception as e:
            error_message = f"Error fetching task data for {task_id}"
            TaskDispatcher.handle_task_failure(worker_id, task_id, error_message)
            self.notify_error(worker_id)
            return 

        try:            
            # Serialize the msg object
            msg = Message(Message.Type.NEW_REDIS_TASK, 
                    worker_id, 
                    ser_func_body = ser_func_body, 
                    ser_func_args = ser_func_args,
                    task_id = task_id,) 
            
            ser_msg = serialize(msg)
            self.socket.send_string(ser_msg) 
            self.replied = True 

            # Add active task to dictionary upon sending
            deadline = time.time() + self.task_timeout
            self.active_tasks[task_id] = [worker_id, deadline]

            # Set status of task to "RUNNING"
            TaskDispatcher.update_task_status(task_id, TaskDispatcher.STATUS.RUNNING)
            print(f"[TASK DISPATCHED] Task {task_id} sent to worker {worker_id} and status:RUNNING")

        except Exception as e:
            error_message = f"Error sending task to a worker {e}"
            TaskDispatcher.handle_task_failure(worker_id, task_id, error_message)
            self.remove_active_task(task_id)
            self.notify_error(worker_id)
            return
        
    def handle_task_completed(self, worker_id, task_id, ser_task_result):
        """
        Updates task result in redis
        upon receiving an update from a 
        pull worker. 
        """
        try:
            # Update redis with result
            TaskDispatcher.update_task_result(task_id, ser_task_result)

            # Update status as complete 
            TaskDispatcher.update_task_status(task_id, TaskDispatcher.STATUS.COMPLETED)

        except Exception as e:
            error_message = f"Error updating COMPLETED task result and status:{e}"
            TaskDispatcher.handle_task_failure(worker_id, task_id, error_message)
            self.remove_active_task(task_id)
            self.notify_error(worker_id)
            return 
        
        # If error occurs when sending acknowledgement
        # We don't want that to be recorded as a func failure 
        try:
            # Remove task from active worker tasks 
            self.remove_active_task(task_id)

            # Send message 
            msg = Message(Message.Type.ACK, worker_id)
            ser_msg = serialize(msg)

            self.socket.send_string(ser_msg)
            self.replied = True 
        except Exception as e:
            self.notify_error(worker_id)
            return 
    
    def handle_task_failed(self, worker_id, task_id, ser_task_result):
        """
        Updates task status in redis upon receiving 
        an update from a pull worker 
        that task has completed running unsuccessfully
        """
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
            self.remove_active_task(task_id)
            self.notify_error(worker_id)
            return 
        
        # If error occurs when sending acknowledgement
        # We don't want that to be recorded as a func failure 
        try:
            # Remove task from active worker tasks 
            self.remove_active_task(worker_id, task_id)

            # Send message 
            msg = Message(Message.Type.ACK, worker_id)
            ser_msg = serialize(msg)

            self.socket.send_string(ser_msg) 
            self.replied = True 
        except Exception as e:
            self.notify_error(worker_id)
            return 

    def notify_error(self, worker_id):
        """
        Send worker a REP that indicates 
        that an error occured on dispatcher side.
        This will ensure worker does not keep
        waiting for REP. 
        """
        if self.replied == False:
            # Send message 
            msg = Message(Message.Type.REQ_FAILED, worker_id)
            ser_msg = serialize(msg)

            self.socket.send_string(ser_msg)
            self.replied = True 
    
    def remove_active_task(self, task_id):
        """
        Removes active task from self.active_tasks when 
        task runs and enters 
        COMPLETED or FAILED state
        """
        # Remove the key and handle if it doesn't exist
        self.active_tasks.pop(task_id, None)
        return

    def check_task_timeout(self):
        """
        Periodically checks for unresponsive workers.
        If the dispatcher detects that a worker hasn't sent a 
        heartbeat within a predefined interval, it marks the 
        worker as unresponsive.
        """
        print("Running task_timeout checks for fault tolerance")

        def monitor_task_timeouts():
            while True:
                now = time.time() # Current time 

                for task_id, task_info in list(self.active_tasks.items()):
                    # Unpack the list into worker_id and deadline
                    # Deadline represents time it should have been removed by
                    worker_id, deadline = task_info  

                    if now > deadline:
                        error_message = f"Task {task_id} failed on worker {worker_id} due to timeout."
                        print(f"[WORKER FAILURE DETECTED]: {error_message}")
                        
                        # Remove tasks from active tasks
                        self.remove_active_task(task_id)

                        # Push error to Redis 
                        TaskDispatcher.handle_worker_failure(worker_id, task_id, error_message)

                time.sleep(0.05)
        
        # Ensures that the health checker runs concurrently 
        # with the main dispatcher process, allowing the dispatcher 
        # to continue handling tasks without being 
        # blocked by the health-checking logic.
        self.checker_thread = threading.Thread(target=monitor_task_timeouts, daemon=True)
        self.checker_thread.start()
    
    def shutdown(self):
        """
        Gracefully shuts down Push task dispatcher
        """
        try:
            print("Shutting down pull task dispatcher")
            # Set running flag to False
            self.running = False

            # Stop the heartbeat thread
            self.checker_thread.join(timeout=1)

            # Close ZeroMQ socket
            self.socket.close()

            # Terminate ZeroMQ context
            self.context.term()

            # Close Redis client
            TaskDispatcher.redis_client.close()

            print("Pull task dispatcher shutdown.")
        except Exception as e:
            print("Error while shutting down pull dispatcher")