# python3 pull_worker.py <num_worker_processors> <dispatcher url>

import signal
import sys
import time
import zmq
import uuid
import concurrent.futures
from threading import Lock

from message import Message
from utils import serialize, deserialize
from failure_exceptions import FunctionFailedException

class PullWorker:
    def __init__(self, num_processors, dispatcher_url): 
        # Id for the worker 
        self.worker_id = "PULL:" + str(uuid.uuid4()) 

        # socket set-up
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(dispatcher_url)
        
        # Initialize the worker details 
        self.num_processors = num_processors
        self.registered = False 
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=num_processors)

        # Lock for socket thread safety
        self.lock = Lock()

        # Track how many threads are already busy 
        self.load = 0 

        # Debug message
        self.running = True 
        print(f"Pull worker connected to pull dispatcher at {dispatcher_url}")
    
    def register_worker(self):
        """
        Registers worker with the TaskDispatcher 
        to ensure it accepts further message requests.
        """
        print("In register function")
        try: 
            # Send REG message to Dispatcher 
            msg = Message(
                msg_type = Message.Type.WORKER_REGISTRATION, 
                worker_id= self.worker_id)
            
            ser_msg = serialize(msg)
            print(msg)

            with self.lock:
                self.socket.send_string(ser_msg)

                # Wait for Message with type ACK
                ser_response = self.socket.recv_string()
                
            # Response is object of Type Message 
            deser_rep = deserialize(ser_response)
            print(deser_rep)
            
            if isinstance(deser_rep, Message):
                if deser_rep.msg_type == Message.Type.ACK:
                    # Ensure acknowledgment was for correct worker 
                    if deser_rep.worker_id == self.worker_id:
                        self.registered = True 
                        print(f"Sucessfully registered worker {self.worker_id}")
                        # It can now start requesting tasks 
                        self.start_worker()
                elif deser_rep.msg_type == Message.Type.REQ_FAILED:
                    # This means worker is not registered
                    # Attempt to register again 
                    self.register_worker()
                else:
                    print(f"Registration of worker {self.worker_id} failed")
            else:
                print(f"Registration of worker {self.worker_id}\
                      failed due to invalid response from PullTaskDispatcher")
        except KeyboardInterrupt:
            print("KeyboardInterrupt received. Shutting down...")
            self.shutdown()
        except Exception as e:
            print(f"Error during worker {self.worker_id} registration: {e}")
    
    def start_worker(self):
        """
        Ready to start sending REQ to Dispatcher
        whenever there are idle threads that can 
        process tasks
        """
        print(f"Starting processing on worker {self.worker_id}")

        try:
            while self.running:
                if self.num_processors > self.load:
                    # If worker is free, get task
                    self.request_task()
                else:
                    print("All worker threads are busy. \
                          Waiting for free threads...")
                    
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("KeyboardInterrupt received. Shutting down...")
            self.shutdown()
        except Exception as e:
            print(f"Error occured in running worker:{e}")
 
    def request_task(self):
        """
        Requests task from Dispatcher if worker is free.
        If task received, sends task for processing.
        """
        try:
            # Send message to request task 
            msg = Message(
                msg_type=Message.Type.WORKER_TASK_REQUEST,
                worker_id=self.worker_id
            )

            ser_msg = serialize(msg)

            with self.lock:
                self.socket.send_string(ser_msg)

                rep = self.socket.recv_string()
        except Exception as e:
            print(f"Error requesting task from Redis:{e}")

        try:
            deser_rep = deserialize(rep)

            if isinstance(deser_rep, Message):
                if deser_rep.worker_id == self.worker_id:
                    if deser_rep.msg_type == Message.Type.NEW_REDIS_TASK:
                        self.process_task(deser_rep)
                    elif deser_rep.msg_type == Message.Type.NO_REMAINING_TASKS:
                        return 
                    else:
                        print(f"Wrong message received {deser_rep.msg_type}")

                else:
                    print(f"Wrong worker ID in message")
        except Exception as e:
            print(f"Error requesting task from Redis:{e}")


    def process_task(self, deser_rep:Message):
        """
        Runs the task on one of the worker threads.
        """
        
        # Indicate that a thread is busy 
        self.load += 1 

        # Extract details of task 
        try:
            ser_func_body = deser_rep.ser_func_body
            ser_func_args = deser_rep.ser_func_args 
            task_id = deser_rep.task_id
        except Exception as e:
            error_message = f"Error when extracting task details from Dispatcher message:{e}"
            self.handle_task_failed(task_id, error_message)
            return 
        
        # Ensure valid func_body and args provided
        # Deserialize the information 
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
        Handles passing on result of task 
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

            print("MESSAGE", msg)

            # Send it to dispatcher 
            ser_msg = serialize(msg)
            with self.lock:
                self.socket.send_string(ser_msg)

                # It should recieve ACK or REQ_FAILED msg
                # We do not need to do further processing on either 
                self.socket.recv_string()
            
            # Indicate that the theread is now available 
            if self.load > 0:
                self.load -= 1 
            
        except Exception as e:
            error_message = f"Error processing task result:{e}"
            self.handle_task_failed(task_id, error_message)
            return 

    def handle_task_failed(self, task_id, error_message, error_code = 500):
        """
        Send message to Dispatcher to indicate that the 
        task has failed due to issues in the function. 
        """
        load_decreased = False 

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
                # Send it to dispatcher 
                self.socket.send_string(ser_msg)

                # Will receive ACK or REQ_FAILED
                # No need to process either 
                self.socket.recv_string()
            
            # Indicate that the the thread is now available 
            if self.load > 0:
                self.load -= 1 
                load_decreased = True 
            
        except Exception as e:
            # Ensure to indicate thread availability 
            if load_decreased == False:
                if self.load > 0:
                    self.load -= 1 
                    load_decreased = True
            error_message = ("Error sending TASK_FAILED message")
            return 
            
    def shutdown(self):
        """Gracefully shutdown the worker
        and the ZMQ Context"""

        try:
            print("Shutting down pull worker...")
            self.running = False 
            self.socket.close()  # Ensure the socket is closed
            self.context.term() # Close the zmq context
            self.executor.shutdown(wait=False) # Do not wait for all tasks to finish
            print("Pull Worker shutdown complete")
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error while shutting down push worker {self.worker_id}:{e}")

if __name__ == '__main__':
    num_workers = int(sys.argv[1])
    dispatcher_url = sys.argv[2]

    try:
        pull_worker = PullWorker(num_workers, dispatcher_url)
        pull_worker.register_worker()
    except Exception as e:
        print(f"Error occured in creating pull worker: {e}")

    def handle_exit(signum, frame):
        pull_worker.shutdown()

    signal.signal(signal.SIGINT, handle_exit) # handle Ctrl+C
    signal.signal(signal.SIGTERM, handle_exit) # handle kill



















