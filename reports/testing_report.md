# Test Report

### Set up Package
Activate virtual environement
- created one and pip install -r requirements

```
conda activate ds_final
```

At root project directory /project-card_readers

Before running the package make sure to remove /build or pycache or pytest cache

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

6.  For testing

        cd app
        pytest tests

        To show debugging message:
        pytest tests --log-cli-level=WARNING

        To show debugging message:
        pytest -s tests

        To test specific function :
        tests/test_xadvanced.py::test_manual_timeout_task


### Test Modules
1. tests/test_webservice.py [RECOMMENDED]
2. tests/test_webservice_ext.py [RECOMMENDED]
3. tests/test_webservice_ext.py

### 1. test_webservice.py
- Test basic functionality including fast endpoints and check task result

### 2. test_webservice_ext.py

- The extended version required dispatcher and workers to be
      configured as mentioned above. The `test_concurrent_tasks` function test can take up to 1 minute.

  Steps:
  ```
  cd app
  pytest tests
  ```

- The test will cover endpoints
    - POST/register_function
    - POST/execute_function
    - GET/status
    - GET/result

1. Registering 5 functions from fn_utils
      - no_op, double, sleep_1s, fibonacci, bruteforce_password
      stores their function_ids for later use

2. test_fastapi_execute_function
      - get task_ids

3. test_fastapi_get_status
      - verify task status

4. test_fastapi_get_result

5. test_fn_registration_invalid
      - Using a non-serialized payload data

6. test_execute_fn_invalid
      - missing argument payload
      result FunctionFailedException
      - Mode : PUSH/ PULL (not work on local)

7. test_execute_fn_invalid_kwarg
      - missing kwarg
      result FunctionFailedException
      - Mode : PUSH/ PULL (not work on local)

### 3. test_advanced.py
##### NOTE: This execution requires carefully following the instructions mentioned and possibly running individual tests as it requires worker and dispatcher to be configured fully
8. test_concurrent_tasks
      - check how many tasks are running concurrently.
      The number should match the number of worker processes.
9. test_manual_timeout_task
      - check that task results in worker failure
      setting dispatcher task timout (=10s)

### Basic Functionality
These are the output from dispatcher and workers when doing the following operations.
- Registration
- Handling tasks
- Multiple workers

1. Registration
PULL mode
![PULL_register](img/PULL_register.png)
PUSH mode
![PUSH_register](img/PUSH_register.png)

2. Handling tasks
![PUSH_handle_task](img/PUSH_handle_task.png)

3. Multiple workers
  - Test checks that 4 processors are available concurrently.
  PULL :

        # terminal 1
        python3 task_dispatcher.py -m pull -p 7001 -t 12

        # terminal 2
        python3 pull_worker.py 2 tcp://localhost:7001

        # terminal 3
        python3 pull_worker.py 2 tcp://localhost:7001

        # terminal 4
        # Submitted 10 concurrent tasks
        pytest tests/test_webservice_ext.py::test_concurrent_tasks
        ```

      ![PULL_multi_workers](img/PULL_multi_workers.png)
      - Observe that equal amount of tasks are distributed between two workers

      PUSH :
      ![PUSH_multi_workers](img/PUSH_multi_workers.png)

---

### Fault Tolerance Test

PULL mode
- Test task timeout on PULL dispatcher

  ```
  cd project-card_readers
  python app/tests/test_webservice_ext.py -log-cli-level=ERROR
  ```
  Output :
  ```
  Pull Timeout Result : Task Timeout Hit
  ```

  Remark : Do not run this test on PUSH mode

PUSH mode

- Test missed Heartbeat by manually killing workers in the terminal

      pytest -s -v tests/test_xadvanced.py::test_manual_timeout_task -log-cli-level=WARNING

  ![PUSH_missed_HB](img/PUSH_missed_HB.png)


  Steps :
  1. Submit a long task
  2. Manually kill the worker while the task is running
  3. Task status should show `WorkerFailureException`
      Verify with POST request on postman or use get_result(task_id)
      Deserialized result output example:

          WorkerFailureException: Worker
          PUSH:0564c6ae-967b-46e0-94c9-ba56cc99ee58 running
          0e9b9c6b-b19c-4ada-ad7f-a7b4a48721a9 failed (missed heartbeat)


---

Tests Checklist :

```
Dispatcher Basic
[X] Test local dispatcher
    - Worker Registration success
    - Send 1 task
    - Send multiple tasks

[X] Test Pull Dispatcher
    - Send 1 task
    - Test send multiple tasks

[X] Test Push Dispatcher
    - Send 1 task
    - Send multiple tasks

[X] Test concurrent execution
      - Send multiple tasks at once
          - Result : max concurrent count == no. of worker processes use

[X] Test Basic :
    - Test Registration PUSH/PULL

[X] Test Fault tolerance :
    PULL :
    - Manual check task time out
        config Pull worker to 12 second time out
        Result : task status fails + error msg

    PUSH :
    - Manual missed heartbeat
        config run Push worker and kill it
        When dispatcher not getting HEARTBEAT -> Task status fail + error msg
        worker marked fail.

Edge Cases
[ ] FunctionFailedException : Send python function that has error
[ ] what are the big things that can go wrong
[ ] high level requirement of the project and see what can be tested
[ ] Serialization error handling
```
