from task_dispatcher import TaskDispatcher
import time 
import multiprocessing
from utils import deserialize, serialize

class LocalTaskDispatcher(TaskDispatcher):
    """_summary_
    Executes tasks locally using multiprocessing pool.

    The Pool class in the multiprocessing module simplifies the 
    parallel execution of functions by managing a pool 
    of worker processes for you. It abstracts away the complexities 
    of process creation and synchronization.

    USAGE:
    For Development/testing

    Args:
        TaskDispatcher (_type_): _description_
    """
    def __init__(self, num_workers):
        super().__init__()
        self.num_workers = num_workers
        self.pool = multiprocessing.Pool(processes=self.num_workers) 
        print(f"Local dispatcher Pool initialized with {self.num_workers} workers.")
        
        # Create a Pub/Sub object for subscribing to channels and 
        # handling messages in the Redis Pub/Sub messaging system.
        self.pubsub = self.redis_client.pubsub()
    
    def initiate_dispatch(self):
        """
        Listens for tasks by subscribing to the redis channel 
        "tasks" that the FaaS service publishes a message to 
        everytime a client requests a task be run
        """
        # Subscribe to the 'tasks' channel
        # Using "with" Ensures that the pool is closed and 
        # joined after tasks are completed, preventing resource leaks.
        self.pubsub.subscribe('tasks')
        print("Subscribed to 'tasks' channel. Waiting for messages...")
        print(" ")
        
        try:
            while True:
                message = self.pubsub.get_message(timeout=1)

                # Filter for actual messages
                # This avoids processing non-message events.
                if message and message["type"] == "message":
                    # Should receive task_id (str)
                    task_id = message['data']

                    if task_id:
                        print(f"[RECEIVED TASK]: {task_id}")
                        self.handle_task("Local", task_id=task_id)

                time.sleep(0.05)
        except KeyboardInterrupt:
            print("KeyboardInterrupt received. Shutting down...")
            self.shutdown()
        except Exception as e:
            print(f"Error while listening for tasks:{e}")

    def handle_task(self, worker_id, task_id:str):
        """
        1. Extracts task information from Redis 
        2. Sends it to be handled by a pool of workers 
        3. Sets status of task in Redis to "Running"
        4. Sets results of task once complete 
        5. Sets task status to "Complete" or "Failed"
        """

        try: 
            # Fetch Task information 
            ser_func_body, ser_func_args = self.fetch_task_data(task_id)

            # Use multiprocessing pool to execute the task
            self.pool.apply_async(
                func = self.execute_task,
                args= (task_id, ser_func_body, ser_func_args,),
                callback=self.on_task_executed
            )

            print(f"[TASK DISPATCHED] {task_id}")
        except Exception as e:
            error_message = f"Error sending task to worker {task_id}: {e}"
            TaskDispatcher.handle_task_failure("LocalWorker", task_id, error_message)
            return

    @staticmethod
    def execute_task(task_id, ser_func_body, ser_func_args):
        """
        Executes the function with the given parameters and
        returns result and status that then gets passed 
        on to a callback_fn in the apply_async functionality.
        """
        # Update task status to "RUNNING" as worker has now accepted a task
        TaskDispatcher.update_task_status(task_id, TaskDispatcher.STATUS.RUNNING)

        valid = True 

        # Deserialize the information 
        try:
            deser_func_body = deserialize(ser_func_body)

            # Inspect the deserialized object to ensure it's a callable (function)
            if not callable(deser_func_body):
                result = f"Deserialized payload is not a callable function {deser_func_body}"
                valid = False
                status = TaskDispatcher.STATUS.FAILED
                print(result)

            deser_func_args = deserialize(ser_func_args)

            # Ensure the deserialized object is a tuple
            if not isinstance(deser_func_args, tuple):
                result = f"Invalid serialized args payload {deser_func_args}"
                valid = False
                status = TaskDispatcher.STATUS.FAILED
                print(result)
            
            # Check validity of args, kwargs 
            if len(deser_func_args) == 2:
                args = deser_func_args[0]
                kwargs = deser_func_args[1]

                if not isinstance(args, tuple):
                    result = f"First element of the tuple (positional arguments) is not a tuple: {args}"
                    valid = False
                    status = TaskDispatcher.STATUS.FAILED
                    print(result)

                if not isinstance(kwargs, dict):
                    result = f"Second element of the tuple (keyword arguments) is not a dictionary: {kwargs}."
                    valid = False
                    status = TaskDispatcher.STATUS.FAILED
                    print(result)

        except Exception as e:
            result = f"Error deserializing task and getting task_details {task_id}: {e}"
            print(result)

        if valid:
            # Prepare for execution
            try:
                result = deser_func_body(*args, **kwargs)
                status = TaskDispatcher.STATUS.COMPLETED
                print("[TASK RESULT]", result, status)
            except Exception as e:
                result = f"Error {e} when executing task {task_id}"
                TaskDispatcher.handle_task_failure("LOCAL", task_id, result)
                print(f"Error {e} when executing task {task_id}")
                status = TaskDispatcher.STATUS.FAILED

        # Serialize result for storing in redis 
        result = serialize(result)  
        return (task_id, status, result)

    def on_task_executed(self, result):
        try: 
            task_id, status, ser_result = result

            # Set result 
            TaskDispatcher.update_task_result(task_id, ser_result)

            # Set status as COMPLETE to indicate it can now be accessed
            # with the result
            TaskDispatcher.update_task_status(task_id, status)

            print(f"[TASK EXECUTED] Task {task_id} ran with status: {status}")
            print("*******************")
        except Exception as e:
            error_message = f"Error updating status of {task_id} after completion: {e}"
            TaskDispatcher.handle_task_failure("LocalWorker", task_id, error_message)
            return

    def shutdown(self):
        """
        Gracefully shuts down Push task dispatcher
        """
        try:
            print("Shutting down local task dispatcher")

            # Set running flag to False
            self.running = False

            # Ensure the pool is closed and joined properly
            self.pool.close()
            self.pool.join(timeout = 1)  # Wait for all workers to complete

            # Ensure the connection is closed
            self.pubsub.close()
            TaskDispatcher.redis_client.close()
            print("Local task dispatcher shutdown.")
        except Exception as e:
            print("Error while shutting down local dispatcher")