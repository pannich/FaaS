from concurrent.futures import ThreadPoolExecutor
import pytest
import requests
import logging
import time
import redis
from .serialize import serialize, deserialize

# *********** FUNCTIONS *********** #
import time
import itertools

def no_op():
    return "DONE"

def sleep_1s():
    time.sleep(1)
    return "Slept"

def sleep_n(n):
    time.sleep(n)
    return f"Slept for {n} seconds"

def double(x):
    return x * 2

def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)

def bruteforce_password(hashed_password, max_length):
    """
    Crack a password hash using brute force.
    Only use ascii lowercase characters for simplicity.

    Usage:
    bruteforce_password('cce6b3fb87d8237167f1c5dec15c3133', 4) #mpcs
    """
    # echo -n mpcs | md5sum
    import string
    import hashlib
    chars = string.ascii_lowercase  # Only lowercase letters for simplicity
    current_index = 0
    end_index = sum(len(chars) ** i for i in range(1, max_length + 1))

    for password_length in range(1, max_length + 1):
        for guess_tuple in itertools.product(chars, repeat=password_length):
            # join the combination of characters to form a guess
            guess = ''.join(guess_tuple)
            hashed_guess = hashlib.md5(guess.encode()).hexdigest()
            if hashed_guess == hashed_password:
                return guess
            current_index += 1
            if current_index >= end_index:
                return None

# *********** CONFIG *********** #
logging.basicConfig(level=logging.WARNING)

base_url = "http://127.0.0.1:8000/"
valid_statuses = ["QUEUED", "RUNNING", "COMPLETED", "FAILED"]
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# *********** REDIS *********** #
def clear_redis():
    redis_client.flushall()

# *********** FAST API *********** #
def register_function(name, payload):
    """returns function_id"""
    resp = requests.post(base_url + "register_function",
                         json={"name": name,
                               "payload": serialize(payload)})
    return resp.json(), resp.status_code

def execute_function(function_id, payload):
    """returns {'task_id': task_id, 'status': status}"""
    resp = requests.post(base_url + "execute_function",
                         json={"function_id": function_id,
                               "payload": serialize(payload)})
    return resp.json()

def get_status(task_id):
    resp = requests.get(f"{base_url}status/{task_id}")

    return resp.json()["status"]

def get_result(task_id):
    """return {'task_id': task_id, 'status': status, 'result': result}"""
    resp = requests.get(f"{base_url}result/{task_id}")
    return resp.json()

# *********** Test FAST API *********** #

@pytest.fixture(scope="module")
def function_ids():
    """Fixture to manage shared state across tests."""
    # Clear Redis before running tests
    clear_redis()

    # Initialize shared variables
    function_ids = {
        "no_op_fn_id": None,
        "double_fn_id": None,
        "sleep_1s_fn_id": None,
        "fibonacci_fn_id": None,
        "bruteforce_password_fn_id": None,
        "sleep_n_fn_id": None
    }

    # Register the functions and store their function_ids
    for func_name in ["no_op", "double", "sleep_1s", "fibonacci", "bruteforce_password", "sleep_n"]:
        resp, status_code = register_function(func_name, globals()[func_name])  # Assuming functions are in the global scope
        print(resp)
        # print(f"\n{func_name}_fn_id: {resp['function_id']}")
        assert status_code in [200, 201]
        assert "function_id" in resp
        function_ids[f"{func_name}_fn_id"] = resp["function_id"]

    # Provide the shared state to the tests
    yield function_ids

@pytest.fixture(scope="module")
def task_ids(function_ids):
    """Fixture to manage shared state across tests."""

    # Initialize shared variables
    task_ids = {
        "no_op": None,
        "double": None,
        "sleep_1s": None,
        "fibonacci": None
    }

    # Execute the functions and store their task_ids
    task_ids["no_op"] = execute_function(function_ids["no_op_fn_id"], ((), {})).get("task_id")
    task_ids["double"] = execute_function(function_ids["double_fn_id"], ((2,), {})).get("task_id")
    task_ids["sleep_1s"] = execute_function(function_ids["sleep_1s_fn_id"], ((), {})).get("task_id")
    task_ids["fibonacci"] = execute_function(function_ids["fibonacci_fn_id"], ((5,), {})).get("task_id")
    task_ids["bruteforce_password"] = execute_function(function_ids["bruteforce_password_fn_id"], (('cce6b3fb87d8237167f1c5dec15c3133', 4), {})).get("task_id")

    for key, task_id in task_ids.items():
        logging.warning(f"\n {key} {task_id}")

    # Provide the shared state to the tests
    yield task_ids


# *********** Test Advance with Manual Config *********** #
### ----- PULL ---- ###

def test_concurrent_tasks(function_ids):
    """
    Submit 6 tasks concurrently to Pull worker that is running on 4 processors.
    First 4 tasks should be running concurrently, the last 2 should be queued.

    Concurrently sleep for 10 seconds, 4 tasks should be running concurrently.

    Config :
    - Pull dispatcher
    - timeout set to 12 seconds
    $ python3 task_dispatcher.py -m pull -p 7001 -t 12

    Step :
    - Restart worker to free worker
    """

    n = 10
    start_times = {}
    end_times = {}
    begin = time.time()

    def execute_task(i):
        task_id = execute_function(function_ids["sleep_n_fn_id"], ((10,), {})).get("task_id")
        while True:
            resp = get_result(task_id)
            # logging.warning(resp)
            if start_times.get(i) == None and resp["status"] == "RUNNING":
                logging.warning(f"Task {i} started")
                start_times[i] = time.time() - begin
            elif resp["status"] == "COMPLETED":
                logging.warning(f"Task {i} completed")
                end_times[i] = time.time() - begin
                assert deserialize(resp["result"]) == "Slept for 10 seconds"
                return task_id
            elif resp["status"] == "FAILED":
                end_times[i] = time.time() - begin
                logging.warning(f"Task {i} failed")
                return task_id
            time.sleep(0.1)  # Poll every 100ms

    with ThreadPoolExecutor(max_workers=n) as executor:
        futures = [executor.submit(execute_task, i) for i in range(n)]
        task_ids = [f.result() for f in futures] #collecting task_id results

    # Check for concurrency
    # Step 1: Create an event timeline
    events = [(start_time, "start", task_id) for task_id, start_time in start_times.items()] + \
            [(end_time, "end", task_id) for task_id, end_time in end_times.items()]
    # Sort events by time (prioritize "end" for the same timestamp)
    # because x[1] == "start" will be False (0) for "end" events
    events.sort(key=lambda x: (x[0], x[1] == "start"))

    # Step 2: Count concurrency
    current_concurrency = 0
    max_concurrency = 0

    for t, event_type, task_id in events:
        if event_type == "start":
            current_concurrency += 1
        elif event_type == "end":
            current_concurrency -= 1
        max_concurrency = max(max_concurrency, current_concurrency)

    # Print results
    logging.warning(f"Maximum concurrency: {max_concurrency}")

    # Assume there are 4 processors available
    num_processors = 4
    buffer = 1
    assert max_concurrency >= num_processors - 1 and max_concurrency <= num_processors + buffer , "Max concurrency should be equal to the number of processors +- 1"

def test_manual_timeout_task(function_ids=None):
    ## WARNING : Only for Pull Mode Test
    """
    Test task failed time out on task by submit a time consuming task.
    Config :
    - Pull dispatcher
    - timeout set to 12 seconds
    $ python3 task_dispatcher.py -m pull -p 7001 -t 12
    - kill worker afterwards to free worker

    """
    fibonacci_payload = serialize(fibonacci)
    arg_payload = serialize(((90,),{}))

    resp = requests.post(base_url + "register_function",
                         json={"name": 'double_manual',
                               "payload": fibonacci_payload})

    fn_id = resp.json()["function_id"]

    resp = requests.post(base_url + "execute_function",
                         json={"function_id": fn_id,
                               "payload": arg_payload})

    timed_out_task_id = resp.json().get("task_id")

    logging.warning(f"Timedout Task ID : {timed_out_task_id}")

    begin = time.time()
    while time.time() - begin < 15:
        status = get_status(timed_out_task_id)
        if status == "RUNNING":
            break
        time.sleep(3)

    time.sleep(15) # wait until task timeout after 12 seconds

    resp = get_result(timed_out_task_id)
    assert resp["status"] == "FAILED", "The task timeout did not hit."

    result = deserialize(resp["result"])
    logging.warning(f"Woker Failure Result: {result}")
    assert "Worker Failure" in str(result), 'Test timeout hit'

### --------- ###
