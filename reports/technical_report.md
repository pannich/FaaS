###### Technical Report
## Function as a Service (FaaS) platform

FaaS is a serverless computing model that allows users to deploy, manage, and execute discrete units of code (functions) without the need to manage underlying server infrastructure. It focuses on event-driven execution, where functions are triggered by specific events or API calls.

### 1. Redis

- A Redis client is initialized to store function and task data.
- Redis serves as:
  - A key-value store for function metadata and task states.
  - A message broker to publish tasks and handle task queues.

**Start redis**

```
redis-server
```

**Redis CLI**
```bash
# Example
redis-cli

# check size
dbsize

# list all keys
keys *

# check if key exists
exists "71ed469b-bc52-45d5-89ae-b21aa40760c9" # return 1 True, 0 False

# get infomation related to this function hash key
hgetall "71ed469b-bc52-45d5-89ae-b21aa40760c9"

# delete key
del "71ed469b-bc52-45d5-89ae-b21aa40760c9"

# clear everything in the db
flushall

```

## Fast API
app/main.py houses all of the end points that are accessed by a client to interact with the FaaS. The following are the endpoints that are supported:

**2.1 Registering Functions**
  - **Endpoint**: POST /register_function
  - **Request Model**: RegisterFn
    - name: Name of the function.
    - payload: Serialized Python function.
  - **Response Model**: RegisterFnRep
    - function_id: A unique UUID for the registered function.
  - **Workflow**:
    - Deserializes and validates the function payload.
    - Stores the function metadata in Redis (name, function_body).
    - Returns a function_id to the client.
  - **Error Handling**:
    - Invalid serialization.
    - Redis connection or operation errors.

**2.2 Executing a Function**
  - **Endpoint**: POST /execute_function
  - **Request Model**: ExecuteFnReq
    - function_id: UUID of the function.
    - payload: Serialized arguments for the function.
  - **Response Model**: ExecuteFnRep
    - task_id: A unique UUID for the submitted task.
  - **Workflow**:
    - Deserializes and validates the arguments payload.
    - Retrieves the function body using function_id from Redis.
    - Creates a task payload containing:
        - `task_id`
        - Function body
        - Input arguments
        - Task status (`QUEUED` initially).
    - Stores the task in Redis and publishes it to workers via:
        - Redis `pub/sub` channel (tasks) for `PUSH` and `LOCAL` modes.
        - Redis queue (task_queue) for `PULL` mode.
    - Returns `task_id` to the client.
  - **Error Handling**:
    - Invalid serialization of arguments.
    - Function not found.
    - Redis connection or operation errors.

**2.3 Task Status Interface**
  - **Endpoint**: GET /status/{task_id}
  - **Response Model**: TaskStatusRep
    - task_id: UUID of the task.
    - status: Current task status (QUEUED, RUNNING, COMPLETED, FAILED).
  - **Workflow**:
    - Retrieves the task status from Redis.
    - Returns the status if the task exists.
  - **Error Handling**:
    - Task not found.
    - Redis connection or operation errors.

**2.4 Task Results Interface**

-   **Endpoint**: `GET /result/{task_id}`
-   **Response Model**: `TaskResultRep`
    -   `task_id`: UUID of the task.
    -   `status`: Task status.
    -   `result`: Serialized result or error message.
-   **Workflow**:
    1.  Retrieves the task result and status from Redis.
    2.  Returns the result and status if the task exists.
-   **Error Handling**:
    -   Task not found.
    -   Redis connection or operation errors.

### 3. Key Features
#### 3.1 Task Lifecycle

-   Tasks transition through the following states:
    -   `QUEUED`: Task is stored and waiting for processing.
    -   `RUNNING`: Task is being executed by a worker.
    -   `COMPLETED`: Task execution succeeded.
    -   `FAILED`: Task execution failed or timed out.

#### **3.2 Modes of Worker Communication**

-   **LOCAL Mode**: Workers execute tasks immediately on available local resources.
-   **PUSH Mode**: Tasks are pushed to available workers via Redis pub/sub channels.
-   **PULL Mode**: Workers pull tasks from a Redis queue.

### **4. Error Handling**

-   **Deserialization Errors**:
    -   Invalid function or arguments payload raises an HTTP `400 Bad Request`.
-   **Redis Errors**:
    -   Connection issues result in HTTP `502 Bad Gateway`.
    -   General Redis errors result in HTTP `500 Internal Server Error`.
-   **Task or Function Not Found**:
    -   Raises an HTTP `404 Not Found`.



### **5. Dispatcher and Workers Communication**

----------

#### **5.1 Local**

-   Tasks are executed immediately on available local worker processes. This utilizes Python's multiprocessing pool and multiprocessing library. The local worker checks the Redis "tasks" channel for messages and submits them to be processed asynchronously to a pool. 
-   **Key Points**:
    -   Minimal communication overhead.
    -   As this is already optimized by Python, it serves as the baseline for performance comparison.

----------

#### **5.2 Push**

-   The **PushDispatcher** assigns tasks to **PushWorkers** as they are detected on redis "tasks" channel. 
-   **Performance**: Depends on task balancing and workers' ability to process tasks.

```
+--------------+          +--------------+
|  Dispatcher  |   --->   |   PushWorker |
+--------------+          +--------------+
      PUSH                 RECEIVES TASK
                           AND EXECUTES
                           TASK CONCURRENTLY

```

##### **Push Dispatcher**

-   Utilizes `zmq.ROUTER` to communicate with workers.

----------

**Flow**:

1.  **Listen and Route Messages from Workers**:

    -   Handle messages based on their type:
	```
    1. WORKER_REGISTRATION -> handle_registration
    2. TASK_COMPLETED -> handle_task_completed
    3. TASK_FAILED -> handle_task_failed
    4. HEARTBEAT -> handle_heartbeat
	```
2.  **Submit Tasks to Workers**:

    -   Listen to Redis `tasks` channel for `task_id`.
    -   Use load balancing to find the least loaded worker in `reg_workers`.
    -   Push task to the worker using `handle_task`.
3.  **Monitor Worker Health** (Concurrent Thread):

    -   Check `reg_workers` for worker heartbeats.
    -   If a worker's heartbeat is missing for too long, mark it as failed and remove it.
    -   Update Redis to indicate the worker failure.

----------

**Key Functions**:

-   **Register Workers**:

    -   Store worker metadata in a dictionary:
	``` python
		reg_workers = {worker_id: {"load": 0,
		"last_heartbeat": time.time(),
		"current_task": set()}}
	```

-   **Load Balancing**:

    -   Find the worker with the minimum load in `reg_workers`. 
-   **Handle Incoming Tasks**:

    -   Fetch function payload and arguments from Redis.
    -   Serialize and send task data to workers using `zmq.ROUTER-DEALER`.
    -   Update worker load and task assignment in `reg_workers`.
-   **Handle Task Completed**:

    -   Update Redis with the task result and status.
    -   Reduce worker load and send an acknowledgment to the worker.
-   **Handle Task Failed**:

    -   Update Redis with the task status as `FAILED`.
    -   Store the exception (`FunctionFailedException`) in Redis.
-   **Handle Heartbeat**:

    -   Update the worker's `last_heartbeat` in `reg_workers`.

----------

##### **Push Worker**

-   Utilizes `zmq.DEALER` to communicate with the dispatcher.

----------

**Flow**:

1.  **Register Worker**:

    -   Register itself with the dispatcher.
2.  **Listen for Messages from Dispatcher**:

    -   Use a `poller` with a timeout to prevent blocking.
    -   If a message is received:

        plaintext

        Copy code

        `If message type == NEW_REDIS_TASK -> process_task`

3.  **Send Heartbeat**:

    -   Regularly send a heartbeat message to the dispatcher every `HEARTBEAT_INTERVAL` (e.g., 5 seconds).

----------

**Key Functions**:

-   **Process Task**:

    -   Deserialize task details.
    -   Execute tasks concurrently using a Python futures executor.
    -   If processors are full, tasks are queued by the executor.
-   **Handle Task Completed**:

    -   Check submitted tasks for completion.
    -   Send `TASK_COMPLETED` messages to the dispatcher.
-   **Handle Task Failed**:

    -   Compose and send a `TASK_FAILED` message with `FunctionFailedException`.

----------

**Limitations**:

-   The dispatcher sends one task at a time, which may cause communication overhead. A batch processing model could improve performance.

----------

#### **5.3 Pull**

-   Workers request tasks from the dispatcher when they are ready.
-   **Performance**: Depends on the efficiency of dispatcher and worker communication.

```
+--------------+          +--------------+
|  Dispatcher  |   <---   |  Pull Worker |
+--------------+          +--------------+
     WAITS                REQUESTS TASK
   FOR REQUEST            AND EXECUTES TASK
                          CONCURRENTLY

```

##### **Pull Dispatcher**

-   Utilizes `zmq.REP` to communicate with workers.

----------

**Flow**:

1.  **Listen for Worker Messages**:

    -   Handle messages based on their type:

        ```
        1. WORKER_REGISTRATION -> handle_registration
        2. WORKER_TASK_REQUEST -> dispatch task or handle_no_task
        3. TASK_COMPLETED -> handle_task_completed
        4. TASK_FAILED -> handle_task_failed
		```

2.  **Monitor Task Timeouts** (Concurrent Thread):

    -   Periodically check for unresponsive workers.
    -   Mark overdue tasks as failed and update Redis.

----------

**Key Functions**:

-   **Register Workers**:

        `reg_workers = set()`

-   **Dispatch Tasks**:

    -   Pop tasks from the Redis `task_queue` using `lpop`.
    -   If no tasks are available, respond with `NO_TASK`.
-   **Handle Task Completed**:

    -   Update Redis with the task result and status.
    -   Send acknowledgment to the worker.
-   **Handle Task Failed**:

    -   Update Redis with the task status as `FAILED`.
    -   Store the exception (`FunctionFailedException`) in Redis.

----------

##### **Pull Worker**

-   Utilizes `zmq.REQ` to request tasks from the dispatcher.

----------

**Flow**:

1.  **Register Worker**:

    -   Register itself with the dispatcher.
2.  **Request Tasks**:

    -   Continuously request tasks from the dispatcher using `zmq.REQ`.
    -   If a task is received:

        `If message type == NEW_REDIS_TASK -> process_task`

3.  **Execute Tasks**:

    -   Run tasks concurrently using an executor.
4.  **Send Heartbeat**:

    -   Send regular heartbeat messages to the dispatcher.
5.  **Handle Task Completion or Failure**:

    -   Notify the dispatcher of completed or failed tasks.


### Set up Package
Activate virtual environement
- created one and pip install -r requirements

```
conda activate ds_final
```

At root project directory /project-card_readers
```
pip install .
```

### Steps

Configurations :

1.  Startup redis server

        redis-server

2. Start MPCS FaaS Service

        cd app
        uvicorn main:app --reload

3.  Go to localhost:8000/docs

        http://localhost:8000/docs

4. Running task dispatcher

        cd app/task_dispatcher

        LOCAL:
        python3 task_dispatcher.py -m local -w 4

        PULL:
        python3 task_dispatcher.py -m pull -p 7001 -t 12

        PUSH:
        python3 task_dispatcher.py -m push -p 7001

5. Running workers

        PULL:
        cd app
        python3 pull_worker.py 4 tcp://localhost:7001

        PUSH :
        python3 push_worker.py 4 tcp://localhost:7001