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

def test_fastapi_register_functions(function_ids):
    """Test to ensure all functions are registered correctly."""
    assert function_ids["no_op_fn_id"] is not None, "no_op function ID should be set."
    assert function_ids["double_fn_id"] is not None, "double function ID should be set."
    assert function_ids["sleep_1s_fn_id"] is not None, "sleep_1s function ID should be set."
    assert function_ids["fibonacci_fn_id"] is not None, "fibonacci function ID should be set."
    assert function_ids["bruteforce_password_fn_id"] is not None, "bruteforce_password function ID should be set."

def test_fastapi_execute_function(task_ids):
    """Test to ensure execute function API returns task_id"""
    assert task_ids["no_op"] is not None, "no_op task ID should be set."
    assert task_ids["double"] is not None, "double task ID should be set."
    assert task_ids["sleep_1s"] is not None, "sleep_1s task ID should be set."
    assert task_ids["fibonacci"] is not None, "fibonacci task ID should be set."
    assert task_ids["bruteforce_password"] is not None, "bruteforce_password task ID should be set."

def test_fastapi_get_status(task_ids):
    for fn_name, task_id in task_ids.items():
        status = get_status(task_id)
        assert status in valid_statuses

def test_fastapi_get_result(task_ids):
    def check_result(fn_name, task_id, expected_result):
        # Check task is finished
        logging.warning(f"\n fn_name : {fn_name} \n task_id: {task_id}")
        while True:
            result = get_result(task_id)
            if result["status"] in ["COMPLETED", "FAILED"]:
                break
            time.sleep(0.01)
        assert result["status"] in ["COMPLETED", "FAILED"]
        deser_result = deserialize(result["result"])
        # Check result
        if result["status"] == "COMPLETED":
            logging.warning(f"\n -> COMPLETED. Result: {deser_result}")
            assert deser_result == expected_result
        else:
            logging.warning(f"\n -> FAILED. Result: {deser_result}")
            assert result["result"] is not None

    for fn_name, task_id in task_ids.items():
        if fn_name == "no_op":
            check_result(fn_name, task_id, "DONE")
        elif fn_name == "double":
            check_result(fn_name, task_id, 4)
        elif fn_name == "sleep_1s":
            check_result(fn_name, task_id, "Slept")
        elif fn_name == "fibonacci":
            check_result(fn_name, task_id, 5)
        elif fn_name == "bruteforce_password":
            check_result(fn_name, task_id, "mpcs")


# *********** Test API Edge Cases *********** #

def test_fn_registration_invalid():
    # Using a non-serialized payload data
    invalid_payload = "raw_function_object_not_serialized"
    resp = requests.post(base_url + "register_function",
                         json={"name": 'double_fail',
                               "payload": invalid_payload})
    assert resp.status_code in [500, 400]

def test_execute_fn_invalid(function_ids):
    """Execute task with missing argument payload
    result should be FunctionFailedException"""
    resp = requests.post(base_url + "execute_function",
                         json={"function_id": function_ids["double_fn_id"],
                               "payload": serialize(((), {}))}) #double required one arg, submitting None
    failed_task_id = resp.json().get("task_id")
    time.sleep(5)
    resp = get_result(failed_task_id)

    deser_result = deserialize(resp["result"])

    assert resp["status"] == "FAILED"
    assert resp["result"] is not None
    assert "Function Failure" in str(deser_result)


def test_execute_fn_invalid_kwarg(function_ids):
    """Execute task with invalid payload
    result should be FunctionFailedException"""

    resp = requests.post(base_url + "execute_function",
                         json={"function_id": function_ids["double_fn_id"],
                               "payload": serialize(((2,),))}) #double required kwargs, submitting None
    failed_task_id = resp.json().get("task_id")
    time.sleep(5)
    resp = get_result(failed_task_id)
    deser_result = deserialize(resp["result"])

    assert resp["status"] == "FAILED"
    assert "Function Failure" in str(deser_result)
    assert deser_result.error_code == 500
