import time
import requests
import os
from .serialize import serialize, deserialize
import csv

import logging
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://127.0.0.1:8000/"
WEAK_SCALING_FACTOR = 5

#*********TASKS************

def no_op_task():
    return f"Task: no_op completed"

def sleep_task():
    time.sleep(1)
    return f"Task: sleep for 1s completed"

def heavy_task():
    result = sum(i ** 2 for i in range(1000000))
    return f"Task: heavy computation completed"

def long_sleep():
    time.sleep(10)
    return f"Task: xheavy sleep for 10s completed"

#*********UTILS**************
# Compute latency (avg time/task)
def latency(times):
    pass
# Compute throughput (tasks/sec)
def throughput(times):
    pass
# Compute efficiency
def efficiency(times):
    pass
# Compute totalTime
def totalTime(times):
    pass

def register_function(fn_name, fn_payload):
    """
    Register function with FaaS and return function_id
    """
    payload = {
        "name": fn_name,
        "payload": serialize(fn_payload)}

    try:
        # Send POST request to the server
        response = requests.post(f"{BASE_URL}/register_function", json=payload)

        # If the response is successful (status code 200)
        if response.status_code == 200:
            response_data = response.json()

            function_id = response_data.get("function_id")

            # print(f"Function registered successfully. Function ID: {function_id}")
            return function_id
    except requests.RequestException as e:
        # Handle request errors (e.g., server down, timeout)
        print(f"An error occurred while sending the request: {e}")
        return None

def get_result(task_id):
    """return {'task_id': task_id, 'status': status, 'result': result}"""
    resp = requests.get(f"{BASE_URL}result/{task_id}")
    return resp.json()

def execute_function(fn_id, task_payload):
    """
    Queuing task for execution on FaaS and return task_id
    """
    payload = {
        "function_id": fn_id,
        "payload": serialize(task_payload)}

    try:
        # Send POST request to the server
        response = requests.post(f"{BASE_URL}/execute_function", json=payload)

        # If the response is successful (status code 200)
        if response.status_code == 200:
            response_data = response.json()
            task_id = response_data.get("task_id")

            # print(f"Task queued successfully. task ID: {task_id}")
            return task_id
    except requests.RequestException as e:
        # Handle request errors (e.g., server down, timeout)
        print(f"An error occurred while sending the request: {e}")
        return None

def write_to_csv(filename, row):
    """
    Appends a row of data to the specified CSV file.
    If the file doesn't exist, it creates it and writes the header first.
    """
    # Define header
    header = ["Mode", "OpType", "nWorkers", "nTasks", "TotalTime"]

    # Check if the file exists
    file_exists = os.path.isfile(filename)

    # Open the file in append mode
    with open(filename, mode="a", newline="") as file:
        writer = csv.writer(file)

        # If file doesn't exist, write the header first
        if not file_exists:
            writer.writerow(header)

        # Write the data row
        writer.writerow(row)

#*********TESTING****************

def test_weak_scaling(workers, optype, mode):
    """
    Config :
    python3 task_dispatcher.py -m local -w <num_worker_processors>

    Usage :
    pytest -s test_client.py::test_strong_scaling --workers=<num_worker_processors> --optype=noop --mode=local
    """
    # Register the functions we will need to use
    NO_OP_FN_ID = register_function("no_op", no_op_task)
    SLEEP_FN_ID = register_function("sleep", sleep_task)
    HEAVY_FN_ID = register_function("heavy", heavy_task)
    XHEAVY_FN_ID = register_function("xheavy", long_sleep)

    if optype == "no_op":
        fn_id = NO_OP_FN_ID
    elif optype == "sleep":
        fn_id = SLEEP_FN_ID
    elif optype == "heavy":
        fn_id = HEAVY_FN_ID
    elif optype == "xheavy":
        fn_id = XHEAVY_FN_ID
    else:
        fn_id = SLEEP_FN_ID

    nTasks = WEAK_SCALING_FACTOR * workers

    start_times = {}
    end_times = {}
    begin = time.time()

    def execute_task(i):
        task_id = execute_function(fn_id, ((), {}))
        print(f"Task {i} submitted")
        while True:
            resp = get_result(task_id)
            # logging.warning(resp)
            if start_times.get(i) == None and resp["status"] == "RUNNING":
                logging.warning(f"Task {i} started")
                start_times[i] = time.time() - begin
            elif resp["status"] == "COMPLETED":
                logging.warning(f"Task {i} completed")
                end_times[i] = time.time() - begin
                deser_result = deserialize(resp["result"])
                assert f"{optype}" in str(deser_result)
                return task_id
            elif resp["status"] == "FAILED":
                end_times[i] = time.time() - begin
                logging.warning(f"Task {i} failed")
                return task_id
            time.sleep(0.1)  # Poll every 100ms

    with ThreadPoolExecutor(max_workers=nTasks) as executor:
        futures = [executor.submit(execute_task, i) for i in range(nTasks)]
        # Blocking call until all tasks completed
        task_ids = [f.result() for f in futures] #collecting task_id results

    print(f"No. Tasks submitted {len(task_ids)}")
    end_time = time.time()

    totalTime = end_time - begin
    print(f"Total time taken for {nTasks} {optype} tasks with {workers} workers: {totalTime}")

    # Write results to the CSV file
    write_to_csv("performance_test.csv", [mode, optype, workers, nTasks, totalTime])

def test_strong_scaling(workers, optype, mode):
    """
    Config :
    python3 task_dispatcher.py -m local -w <num_worker_processors>

    Usage :
    * use xheavy for strong scaling
    pytest -s test_client.py::test_strong_scaling --workers=<num_worker_processors> --optype=xheavy --mode=local
    """
    NO_OP_FN_ID = register_function("no_op", no_op_task)
    SLEEP_FN_ID = register_function("sleep", sleep_task)
    HEAVY_FN_ID = register_function("heavy", heavy_task)
    XHEAVY_FN_ID = register_function("xheavy", long_sleep)

    if optype == "no_op":
        fn_id = NO_OP_FN_ID
    elif optype == "sleep":
        fn_id = SLEEP_FN_ID
    elif optype == "heavy":
        fn_id = HEAVY_FN_ID
    elif optype == "xheavy":
        fn_id = XHEAVY_FN_ID
    else:
        fn_id = SLEEP_FN_ID

    nTasks = 20

    start_times = {}
    end_times = {}
    begin = time.time()

    def execute_task(i):
        task_id = execute_function(fn_id, ((), {}))
        while True:
            resp = get_result(task_id)
            # logging.warning(resp)
            if start_times.get(i) == None and resp["status"] == "RUNNING":
                logging.warning(f"Task {i} started")
                start_times[i] = time.time() - begin
            elif resp["status"] == "COMPLETED":
                logging.warning(f"Task {i} completed")
                end_times[i] = time.time() - begin
                deser_result = deserialize(resp["result"])
                assert f"{optype}" in str(deser_result)
                return task_id
            elif resp["status"] == "FAILED":
                end_times[i] = time.time() - begin
                logging.warning(f"Task {i} failed")
                return task_id
            time.sleep(0.1)  # Poll every 100ms

    with ThreadPoolExecutor(max_workers=nTasks) as executor:
        futures = [executor.submit(execute_task, i) for i in range(nTasks)]
        # Blocking call until all tasks completed
        task_ids = [f.result() for f in futures] #collecting task_id results

    print(len(task_ids))
    end_time = time.time()

    totalTime = end_time - begin
    print(f"Total time taken for {nTasks} {optype} tasks with {workers} workers: {totalTime}")

    # Write results to the CSV file
    write_to_csv("performance_test.csv", [mode, optype, workers, nTasks, totalTime])
