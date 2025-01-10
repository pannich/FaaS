# python3 push_worker.py <num_worker_processors> <dispatcher url>
import signal
import sys
import time
import zmq
import uuid
import concurrent.futures
from threading import Lock, Thread

from message import Message
from utils import serialize, deserialize
from failure_exceptions import FunctionFailedException
import config

class PushWorker:
    def __init__(self, num_processors, dispatcher_url):
        # ID for the worker
        self.worker_id = "PUSH:" + str(uuid.uuid4())

        # Socket set-up
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER) 

        # Dealer message is prefixed with worker_id
        self.socket.setsockopt(zmq.IDENTITY, self.worker_id.encode())
        self.socket.connect(dispatcher_url)

        # To use socket in a threadsafe manner 
        self.lock = Lock()

        # Initialize the worker details
        self.num_processors = num_processors
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=num_processors)

        # Debug message
        self.running = True
        print(f"Push worker connected to Push dispatcher at {dispatcher_url}")

        # Setup heartbeat mechanism 
        self.heartbeat_thread = None 
        self.send_heartbeats()

    def register_worker(self):
        """
        Registers worker with the TaskDispatcher and 
        starts listening for tasks pushed to the worker. 
        """
        try :
            # Register worker with dispatcher
            msg = Message(
                msg_type = Message.Type.WORKER_REGISTRATION,
                worker_id= self.worker_id)

            ser_msg = serialize(msg)

            with self.lock:
                # Encode string into bytes and send
                self.socket.send_multipart([b"", ser_msg.encode()])

                # Receive response 
                _, ser_response = self.socket.recv_multipart()

            ser_response = ser_response.decode()

            # Response is object of Type Message
            deser_rep = deserialize(ser_response)

            # If the registration is successful, start push worker.
            if isinstance(deser_rep, Message):
                if deser_rep.msg_type == Message.Type.ACK:
                    print(f"Sucessfully registered worker {self.worker_id}")
                    # It can now start receiving tasks
                    self.listening_to_dispatcher()
                elif deser_rep.msg_type == Message.Type.REQ_FAILED:
                    # This means worker is not registered
                    # Attempt to register again
                    self.register_worker()
                else:
                    print(f"Registration of worker {self.worker_id}\
                    failed due to invalid response from PullTaskDispatcher")
            else:
                print(f"Registration of worker {self.worker_id} failed")
        except KeyboardInterrupt:
            print("KeyboardInterrupt received. Shutting down...")
            self.shutdown()
        except Exception as e:
            print(f"Error during worker {self.worker_id} registration: {e}")

    def listening_to_dispatcher(self):
        """
        Waiting for tasks from dispatcher
        """
        print("Listening for tasks from Push Dispatcher")
        try:
            while self.running:
                try:
                    multipart_msg = self.socket.recv_multipart(flags=zmq.NOBLOCK)
                    _, ser_task_data = multipart_msg
                    ser_task_data = ser_task_data.decode()
                    
                    if ser_task_data:
                        # Deserialize into a Message object 
                        deser_task_data = deserialize(ser_task_data)
                        if not isinstance(deser_task_data, Message):
                            print("Message received by push dispatcher is not of Message Class type")
                            continue
                        print("RECEIVED FROM", deser_task_data)

                        self.process_task(deser_task_data)
                except zmq.Again:
                    # No messages from workers, continue
                    continue
                except zmq.error.ZMQError as e:
                    print(f"ZMQ error: {e}")
                    if e.errno == zmq.ETERM:
                        break
                except Exception as e:
                    print(f"Error while listening for tasks:{e}")
        except KeyboardInterrupt:
            print("KeyboardInterrupt received. Shutting down...")
            self.shutdown()
        except Exception as e:
            print(f"Error while listening for tasks:{e}")

    def process_task(self, deser_rep:Message):
        """
        Runs the task on the worker executor.
        """
        # Tasks beyond the number of available workers are queued until workers are free.
        # Extract details of task
        try:
            ser_func_body = deser_rep.ser_func_body
            ser_func_args = deser_rep.ser_func_args
            task_id = deser_rep.task_id
        except Exception as e:
            error_message = f"Error when extracting task details from Dispatcher message:{e}"
            self.handle_task_failed(task_id, error_message)
            return

        # Deserialize the information \
        # and check for task failure
        try:
            deser_func_body = deserialize(ser_func_body)

            # Inspect the deserialized object to ensure it's a callable (function)
            if not callable(deser_func_body):
                error_message = f"Deserialized payload is not a callable function {deser_func_body}"
                self.handle_task_failed(task_id, error_message)
                return

            deser_func_args = deserialize(ser_func_args)

            # Ensure the deserialized object is a tuple
            if not isinstance(deser_func_args, tuple):
                error_message = f"Invalid serialized args payload {deser_func_args}"
                self.handle_task_failed(task_id, error_message)
                return

            # Check validity of args, kwargs
            if len(deser_func_args) == 2:
                args = deser_func_args[0]
                kwargs = deser_func_args[1]

                if not isinstance(args, tuple):
                    error_message = f"First element of the tuple (positional arguments) is not a tuple: {args}"
                    self.handle_task_failed(task_id, error_message)
                    return

                if not isinstance(kwargs, dict):
                    error_message = f"Second element of the tuple (keyword arguments) is not a dictionary: {kwargs}."
                    self.handle_task_failed(task_id, error_message)
                    return
            else:
                error_message = f"Error getting task params:args or kwargs missing"
                self.handle_task_failed(task_id, error_message)
                return
        except Exception as e:
            error_message = f"Error deserializing task {task_id} and getting task info: {e}"
            self.handle_task_failed(task_id, error_message)
            return

        # Run task 
        try:
            print("***************")
            print(f"Processing task {task_id}")
            future = self.executor.submit(deser_func_body, *args, **kwargs) 
            print(f"Executing task {task_id}")
            future.add_done_callback(lambda fut: self.handle_task_completed(fut, task_id))
        except Exception as e:
            error_message = f"Error processing task {task_id}: {e}"
            self.handle_task_failed(task_id, error_message)

    def handle_task_completed(self, future, task_id):
        """
        Handles passing on result of task to Push Dispatcher
        after executor has processed it
        """
        print(f"Completed task {task_id}")
        print("***************")
        try: 
            # Get result of task running
            result = future.result()

            # Serialize the result 
            ser_res = serialize(result)

            # Store it in message.task_result 
            msg = Message(
                msg_type= Message.Type.TASK_COMPLETED,
                worker_id=self.worker_id,
                task_id=task_id,
                ser_task_result=ser_res
            )

            # Send it to dispatcher 
            ser_msg = serialize(msg)

            with self.lock:
                # Encode string into bytes and send
                self.socket.send_multipart([b"", ser_msg.encode()])
        except Exception as e:
            error_message = f"Error sending task result completed status:{e}"
            self.handle_task_failed(task_id, error_message)
            return 

    def handle_task_failed(self, task_id, error_message, error_code = 500):
        """
        Send message to Dispatcher to indicate that the
        task has failed due to issues in the function.
        """
        try:
            print(error_message)

            # Create an object of type FunctionFailureException
            exc = FunctionFailedException(self.worker_id, task_id, error_message)

            # Serialize exception (result)
            ser_exc = serialize(exc)

            # Store it in message.task_result
            msg = Message(
                msg_type= Message.Type.TASK_FAILED,
                worker_id=self.worker_id,
                task_id=task_id,
                ser_task_result=ser_exc
            )

            ser_msg = serialize(msg)

            with self.lock:
                # Encode string into bytes and send
                self.socket.send_multipart([b"", ser_msg.encode()])

        except Exception as e:
            error_message = ("Error sending TASK_FAILED message")
            return
    
    def send_heartbeats(self):
        """
        Sends a heartbeat every HEARTBEAT_INTERVAL seconds
        """

        def send_heartbeat():
            try:
                while True:
                    # Store it in message.task_result
                    msg = Message(
                        msg_type= Message.Type.HEARTBEAT,
                        worker_id=self.worker_id,
                    )

                    ser_msg = serialize(msg)

                    with self.lock:
                        # Encode string into bytes and send
                        self.socket.send_multipart([b"", ser_msg.encode()])

                    time.sleep(config.HEARTBEAT_INTERVAL)
            except Exception as e:
                print(f"Error sending heartbeat from worker {self.worker_id}:{e}")

        self.heartbeat_thread = Thread(target=send_heartbeat, daemon=True)
        self.heartbeat_thread.start()

    def shutdown(self):
        """
        Gracefully shutdown the worker
        """
        try: 
            print(f"Shutting push worker {self.worker_id}")
            self.running = False

            # Stop the heartbeat thread
            self.heartbeat_thread.join(timeout=1)

            self.executor.shutdown(wait=False) 

            # Close ZeroMQ socket
            self.socket.close()

            # Terminate ZeroMQ context
            self.context.term()

            print(f"Push worker {self.worker_id} shutdown complete")
        except Exception as e:
            print("Error while shutting down push worker")

if __name__ == '__main__':
    num_workers = int(sys.argv[1])
    dispatcher_url = sys.argv[2]

    try :
        push_worker = PushWorker(num_workers, dispatcher_url)
        push_worker.register_worker()
    except Exception as e:
        print(f"Error occured in creating pull worker: {e}")
    

    def handle_exit(signum, frame):
        push_worker.shutdown()

    signal.signal(signal.SIGINT, handle_exit) # handle Ctrl+C
    signal.signal(signal.SIGTERM, handle_exit) # handle kill