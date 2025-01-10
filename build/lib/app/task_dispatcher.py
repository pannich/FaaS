import argparse
from abc import ABC, abstractmethod
import redis 
from utils import serialize
from failure_exceptions import WorkerFailureException, FunctionFailedException
import signal

"""_summary_
    FUNCTION:
    1. Starts appropriate dispatcher based on the mode indicated by user.
    2. Routes tasks from Redis to workers.
    2. Detects worker failures.
    3. Updates Redis with status, and results when they are available.

    USAGE:
    python3 task_dispatcher.py -m [local/pull/push] -p <port> -w <num_worker_processors>
"""

class TaskDispatcher(ABC):
    class STATUS:
        QUEUED = 'QUEUED'
        RUNNING = 'RUNNING'
        COMPLETED = 'COMPLETED'
        FAILED = 'FAILED'
        
    """
    Abstract Base Class that enforces methods be implemented 
    by dispatchers working in the local, pull, push mode. 
    """
    # Making client a class variable so it can be accessed in static methods 
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def initiate_dispatch(self):
        """
        Responsible for getting task from Redis either by listening 
        for messages on the "tasks" channel or on getting a request 
        from the pull workers. It then starts the dispatching of the
        requests. 
        """
        pass

    @abstractmethod
    def handle_task(self, worker_id:str, task_id:str):
        """
        Send task to worker for execution
        """
        pass 
    
    @staticmethod
    def fetch_task_data(task_id:str):
        """
        Fetch task data currently stored in redis as a hash map 
        of following format 
        task_payload = {
            "task_id": str(task_id), 
            "function_body": function_body, # client-serialized function body
            "function_args": request.payload,  # client-serialized input parameters
            "task_status": "QUEUED",
            "task_result": "None"
        }

        Returns serialized func_body and func_args
        """

        ser_func_body = TaskDispatcher.redis_client.hget(task_id, "function_body")
        ser_func_args = TaskDispatcher.redis_client.hget(task_id, "function_args")

        if not ser_func_body:
            print(f"Function body not found for task ID: {task_id}")
            return 

        if not ser_func_args:
            print(f"Function args not found for task ID: {task_id}")
            return

        return ser_func_body, ser_func_args

    @staticmethod
    def update_task_status(task_id:str, new_status:str):
        """
        Updates task status from old to new 
        """
        cur_status = TaskDispatcher.redis_client.hget(task_id, "task_status")
        if cur_status == TaskDispatcher.STATUS.COMPLETED or cur_status == TaskDispatcher.STATUS.FAILED:
            return 
        try:
            TaskDispatcher.redis_client.hset(task_id, "task_status", new_status)
        except Exception as e:
            print(f"Error {e} when updating status for task {task_id}")

    @staticmethod    
    def update_task_result(task_id, ser_result):
        """
        Updates task result (in serialized format)
        """
        cur_status = TaskDispatcher.redis_client.hget(task_id, "task_status")
        if cur_status == TaskDispatcher.STATUS.COMPLETED or cur_status == TaskDispatcher.STATUS.FAILED:
            return 
        try:
            TaskDispatcher.redis_client.hset(task_id, "task_result", ser_result)
        except Exception as e:
            print(f"Error {e} when updating result for task {task_id}")
            
    @staticmethod
    def handle_task_failure(worker_id, task_id, error_message, error_code = 500):
        cur_status = TaskDispatcher.redis_client.hget(task_id, "task_status")
        if cur_status == TaskDispatcher.STATUS.COMPLETED or cur_status == TaskDispatcher.STATUS.FAILED:
            return 

        exc = FunctionFailedException(worker_id, task_id, error_message, error_code)
        result = serialize(exc)
        
        print(f"FunctionFailureException: {error_message}")

        # Task result will now be the exception object 
        TaskDispatcher.update_task_result(task_id, result)
        TaskDispatcher.update_task_status(task_id, TaskDispatcher.STATUS.FAILED)
    
    @staticmethod
    def handle_worker_failure(worker_id, task_id, error_message, error_code = 500):
        cur_status = TaskDispatcher.redis_client.hget(task_id, "task_status")
        if cur_status == TaskDispatcher.STATUS.COMPLETED or cur_status == TaskDispatcher.STATUS.FAILED:
            return 
        
        exc = WorkerFailureException(worker_id, task_id, error_message, error_code)
        result = serialize(exc)
        
        print(f"WorkerFailureException: {error_message}")

        # Task result will now be the exception object 
        TaskDispatcher.update_task_result(task_id, result)
        TaskDispatcher.update_task_status(task_id, TaskDispatcher.STATUS.FAILED)

def main():
    from local_task_dispatcher import LocalTaskDispatcher
    from push_task_dispatcher import PushTaskDispatcher
    from pull_task_dispatcher import PullTaskDispatcher
    
    parser = argparse.ArgumentParser()

    parser.add_argument('-m', type=str, help='Choose among local/pull/push')
    parser.add_argument('-p', type=int, help='[PULL or PUSH MODE ONLY] The port that the dispatcher runs on')
    parser.add_argument('-w', type=int, help='[LOCAL MODE ONLY] The number of workers to be spawned in the pool')
    # Timeout flag for PULL mode only
    parser.add_argument('-t', type=int, 
                        help='[PULL MODE ONLY] Timeout in seconds for tasks in PULL mode')
    
    arguments = parser.parse_args()

    # Validate that -t is only used with PULL mode
    if not arguments.t and arguments.m == 'pull':
        print("Error: Please provide -t (timeout) flag to use in PULL mode to check when a task should be comsidered failed.")
        return 
    
    # Debugging print statements for testing
    print("************DISPATCHER***************")
    print(f"Mode: {arguments.m}")
    print(f"Port: {arguments.p}")
    print(f"Workers: {arguments.w}")
    print(f"Timeout: {arguments.t}")
    print("*************************************")

    if arguments.m == 'local':
        print(f"Running in LOCAL mode with {arguments.w} worker(s)")
        taskDispatcher = LocalTaskDispatcher(arguments.w)
    elif arguments.m == 'pull':
        print(f"Running in PULL mode on port {arguments.p} with timeout: {arguments.t}s")
        taskDispatcher = PullTaskDispatcher(arguments.p, arguments.t)
    elif arguments.m == 'push':
        taskDispatcher = PushTaskDispatcher(arguments.p)
    else:
        print(f"Invalid mode: {arguments.m}. Choose among local, pull, or push.")

    # Start dispatcher in indicated mode 
    try :
        taskDispatcher.initiate_dispatch()
    except Exception as e:
        print(f"Error in dispatching tasks: {e}")
    
    def handle_exit(signum, frame):
        taskDispatcher.shutdown()

    signal.signal(signal.SIGINT, handle_exit) # handle Ctrl+C
    signal.signal(signal.SIGTERM, handle_exit) # handle kill

if __name__ == '__main__':
    main()





    


