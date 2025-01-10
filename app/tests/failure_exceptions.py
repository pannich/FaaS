class FunctionFailedException(Exception):
    def __init__(self, worker_id, task_id, error_message, error_code=500):
        self.worker_id = worker_id
        self.task_id = task_id
        self.error_message = error_message
        self.error_code = error_code
        super().__init__(f"Task {task_id} failed on worker {worker_id}: {error_message}")

    # def __reduce__(self):
    #     # Specify how to reconstruct the object during deserialization
    #     return (
    #         self.__class__,
    #         (self.worker_id, self.task_id, self.error_message, self.error_code),
    #     )
    
    def __str__(self):
        # Custom string representation (when using print() or str())
        return "EXCEPTION:"+ str({
            "exceptionType": "Function Failure",
            "worker_id": self.worker_id,
            "task_id": self.task_id,
            "error_message": self.error_message,
            "error_code": self.error_code
        })

    def __repr__(self):
        # Custom representation (useful in debugging or REPL)
        return f"FunctionFailedException({str(self)})"
    
class WorkerFailureException(Exception):
    def __init__(self, worker_id, task_id, error_message, error_code = 500):
        self.worker_id = worker_id
        self.task_id = task_id
        self.error_message = error_message
        self.error_code = error_code
        super().__init__(f"Worker {worker_id} failed. "
                         f"Task: {task_id or 'Unknown'}. Reason: {error_message or 'Unknown'}")
    
    def __reduce__(self):
        # Specify how to reconstruct the object during deserialization
        return (
            self.__class__,  # Callable to reconstruct the object (the class itself)
            (self.worker_id, self.task_id, self.error_message, self.error_code),
        )
    
    def __str__(self):
        # Custom string representation (when using print() or str())
        return "EXCEPTION:"+ str({
            "exceptionType": "Worker Failure",
            "worker_id": self.worker_id,
            "task_id": self.task_id,
            "error_message": self.error_message,
            "error_code": self.error_code
        })

    def __repr__(self):
        # Custom representation (useful in debugging or REPL)
        return f"WorkerFailedException({str(self)})"
    
