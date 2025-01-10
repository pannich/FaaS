# Message Protocol
class Message:
    class Type:
        WORKER_REGISTRATION = 'WORKER_REGISTRATION'
        NEW_REDIS_TASK = 'NEW_REDIS_TASK'
        WORKER_TASK_REQUEST = 'WORKER_TASK_REQUEST'
        TASK_COMPLETED = 'TASK_COMPLETED'
        TASK_FAILED = "TASK_FAILED"
        HEARTBEAT = 'HEARTBEAT'
        ACK = 'ACK'
        NO_REMAINING_TASKS = "NO_REMAINING_TASKS"
        REQ_FAILED = "REQ_FAILED"

        # Add a set of valid types for validation
        VALID_TYPES = {WORKER_REGISTRATION, 
                       NEW_REDIS_TASK, 
                       WORKER_TASK_REQUEST, 
                       TASK_COMPLETED, 
                       HEARTBEAT, 
                       ACK, 
                       NO_REMAINING_TASKS, 
                       TASK_FAILED,
                       REQ_FAILED}

    def __init__(self, msg_type, worker_id: str, ser_func_body=None, ser_func_args=None, 
                 task_id = None, ser_task_result=None):
        # Validate the message type
        if msg_type not in self.Type.VALID_TYPES:
            raise ValueError(f"Invalid message type: {msg_type}")
        
        self.msg_type = msg_type
        self.worker_id = worker_id # ID of the worker being communicated with 
        self.task_id = task_id
        self.ser_func_body = ser_func_body
        self.ser_func_args = ser_func_args
        self.ser_task_result = ser_task_result # Ensure in ser format 

    def __str__(self):
        return f'{self.worker_id} - [{self.msg_type}]'
