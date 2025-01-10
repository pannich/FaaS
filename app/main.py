from fastapi import FastAPI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import uuid
from utils import deserialize
from task_dispatcher import TaskDispatcher


app = FastAPI()

# Create a Redis client 
# decode_responses determines whether responses from the 
# Redis server should be automatically decoded from bytes to strings.
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# *********** REGISTERING FUNCTIONS *********** #

# Defining Pydantic models for request and response validation
# REF: https://docs.pydantic.dev/latest/

# This is the request model that the client uses to send 
# function data to the server.
class RegisterFn(BaseModel):
    name: str # Name of function 
    payload: str # Client-serialized function body

# This is the response model that the server uses to respond 
# to the client after successfully registering the function.
class RegisterFnRep(BaseModel):
    function_id: uuid.UUID  

# Endpoint 
# After processing the request, the server will send back data 
# formatted according to the RegisterFnRep Pydantic model.
# Using async in FastAPI allows the application to handle concurrent requests efficiently
# allowing the server to handle a request without blocking other requests
@app.post("/register_function", response_model=RegisterFnRep)
async def register_function(request: RegisterFn):
    # Generate a unique UUID
    function_id = uuid.uuid4()

    # Check if payload is properly serialized by client 
    try:
        # Validate that the payload is serialized properly by attempting to deserialize it
        function_obj = deserialize(request.payload)
        
    except Exception as e:
        # If deserialization fails, return an error response
        raise HTTPException(status_code=400, detail=f"Invalid serialized function_body payload: {e}")

    try:
        # Store function_data in Redis as a hash
        # Allows you to retrieve just a specific field (name, payload) later
        # NOTE key is function:{function_id}
        redis_client.hset(str(function_id), mapping={
            "name": request.name, # str
            "function_body": request.payload # Client-serialized function body
        })

        return RegisterFnRep(function_id=function_id)
    except redis.ConnectionError as e:
        # Redis connection error (e.g., if Redis server is not reachable)
        raise HTTPException(status_code=502, detail=f"Redis connection failed: {e}")
    except redis.RedisError as e:
        # Catch any other Redis-related errors
        raise HTTPException(status_code=500, detail=f"Internal Redis error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Function registration failed: {e}")

# *********** EXECUTING A FUNCTION *********** #  
# Request and response models
class ExecuteFnReq(BaseModel):
    function_id: uuid.UUID
    # tuple ((args), {kwargs})
    payload: str # client-serialized input arguments

class ExecuteFnRep(BaseModel):
    task_id: uuid.UUID

# Endpoint 
@app.post("/execute_function", response_model=ExecuteFnRep)
async def execute_function(request: ExecuteFnReq):
    
    # Check if payload is properly serialized by client 
    try:
        # Validate that the payload(args) is serialized properly by attempting to deserialize it
        args_obj = deserialize(request.payload)

    except Exception as e:
        # If deserialization fails, return an error response
        raise HTTPException(status_code=400, detail=f"Invalid serialized args payload: {e}")
    
    try: 
        # STEP 1: get(key) is used for retrieving values associated with a single key-value pair
        function_body = redis_client.hget(str(request.function_id), "function_body")
        
        if not function_body:
            raise HTTPException(status_code=404, detail="Function not found")
        
        # function_data is {name:str, payload: str(serialized func body)}
        # Step 3: Generate a new UUID for this task
        task_id = uuid.uuid4()

        # Step 4: Compose a task 
        task_payload = {
            "task_id": str(task_id), 
            "function_body": function_body, # client-serialized function body
            "function_args": request.payload,  # client-serialized input parameters
            "task_status": TaskDispatcher.STATUS.QUEUED,
            "task_result": "None"
        }

        # Step 5: Store the task payload in Redis
        redis_client.hset(str(task_id), mapping=task_payload)

        # REF: https://redis.io/docs/latest/commands/publish/
        # Step 6: Publish the task to the "tasks" channel
        # This channel will be used my "PUSH" and "LOCAL" modes
        redis_client.publish("tasks", str(task_id))

        # Add tasks to a redis queue
        # RPUSH adds an element to the end of the queue
        # LPOP Removes and returns the first element of the queue 
        # This will be used by "PULL" mode
        redis_client.rpush("task_queue", str(task_id))

        # Step 7: Return the task ID to the client
        return ExecuteFnRep(task_id=task_id)

    except redis.ConnectionError as e:
        # Redis connection error (e.g., if Redis server is not reachable)
        raise HTTPException(status_code=502, detail=f"Redis connection failed: {e}")
    except redis.RedisError as e:
        # Catch any other Redis-related errors
        raise HTTPException(status_code=500, detail=f"Internal Redis error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Function execution failed: {e}")

# *********** STATUS INTERFACE *********** # 
class TaskStatusRep(BaseModel):
    task_id: uuid.UUID
    status: str

# Endpoint 
@app.get("/status/{task_id}", response_model=TaskStatusRep)
async def task_status(task_id: uuid.UUID):
    try:
        # Look up task status in redis 
        task_status = redis_client.hget(str(task_id), "task_status")

        # Check if task exists in Redis 
        if not task_status:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Return the task status in the response model
        return TaskStatusRep(task_id=task_id, status=task_status)
    except redis.ConnectionError as e:
        # Redis connection error (e.g., if Redis server is not reachable)
        raise HTTPException(status_code=502, detail=f"Redis connection failed: {e}")
    except redis.RedisError as e:
        # Catch any other Redis-related errors
        raise HTTPException(status_code=500, detail=f"Internal Redis error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task Status fetching failed: {e}")

# *********** RESULTS INTERFACE *********** #  
class TaskResultRep(BaseModel):
    task_id: uuid.UUID
    status: str
    result: str

@app.get("/result/{task_id}", response_model=TaskResultRep)
async def task_result(task_id: uuid.UUID):
    try:
        # Look up task status and result(serialized) in redis 
        task_result, task_status = redis_client.hmget(str(task_id), ["task_result", "task_status"])

        # Check if task exists in Redis 
        if not task_result:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Return the task status in the response model
        return TaskResultRep(task_id=str(task_id), status=task_status, result=task_result)
    except redis.ConnectionError as e:
        # Redis connection error (e.g., if Redis server is not reachable)
        raise HTTPException(status_code=502, detail=f"Redis connection failed: {e}")
    except redis.RedisError as e:
        # Catch any other Redis-related errors
        raise HTTPException(status_code=500, detail=f"Internal Redis error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task Result fetching failed: {e}")







