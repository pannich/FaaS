# MPCS-52040 Fall 2024 FaaS Platform Grading Report

## Grader Report:

Total pts: [80/80 pts]

### Technical Report [10/10 pts]

    API: [2/2 pts]
    Architecture: [2/2 pts]
    Functionality: [2/2 pts]
    Design considerations: [2/2 pts]
    Clarity: [2/2 pts]

    This is one of the best write-ups in batch of projects.

    The writeup covers the API, architecture, and components.
    Design decisions concerning performance, fault-tolerance, and limitations are covered in detail.
    Overall, this is done very well.


### Performance Report and Client [10 + 2 / 10pts]


    Who doesn't love plots :) Great job on the performance analysis. This is what we hope to see once you've
    got an interesting system that you've built.

    It looks like you went with a weak scaling study measuring latency, throughput, overhead and efficiency.
    You've covered more metrics than the rest of the batch, and the experimental results are solid.
    You are comparing these metrics between the different modes, and we push doing well on throughput but
    not so well on efficiency. This is exactly what this project aims to have you thinking about.
    I'll add +2 extra points for effort here.

    While evaluating a system of this scale, it is important to consider other measures that can be used.
    You've covered latency (your definition isn't quite what most technical papers use), throughput,
    and overhead. Again, you've probably got the most extensive suite of evaluation metrics in this batch.
    Great job!

    For future projects consider doing a stress test to truly test the limits of your system.

    As you'd expect push overhead is higher than pull overhead. Although negative numbers hint at inaccurate
    timings. This is nicely done, and there's little to critique here.


### Testing Report and tests [ 59 /60 pts]

    I am able to run most of the tests with the different modes, however there are some that consistently
    fail. Apart from that I see that you have added quite a few tests, which is wonderful.

    I can see a significant number of tests passing and that is pretty much sufficient to say that
    you've got all the functionality we care about working except some of the fault tolerance aspects.
    I will deduct 1 pt for these failing tests.

## Automated tests:

### Local mode tests    

                        [ 14%]
    tests/test_webservice.py::test_execute_fn PASSED                                                        [ 21%]
    tests/test_webservice.py::test_roundtrip PASSED                                                         [ 28%]
    tests/test_webservice.py::test_roundtrip_result PASSED                                                  [ 35%]
    tests/test_webservice_ext.py::test_fastapi_register_functions PASSED                                    [ 42%]
    tests/test_webservice_ext.py::test_fastapi_execute_function PASSED                                      [ 50%]
    tests/test_webservice_ext.py::test_fastapi_get_status PASSED                                            [ 57%]
    tests/test_webservice_ext.py::test_fastapi_get_result PASSED                                            [ 64%]
    tests/test_webservice_ext.py::test_fn_registration_invalid PASSED                                       [ 71%]
    tests/test_webservice_ext.py::test_execute_fn_invalid FAILED                                            [ 78%]
    tests/test_webservice_ext.py::test_execute_fn_invalid_kwarg FAILED                                      [ 85%]
    tests/test_xadvanced.py::test_concurrent_tasks PASSED                                                   [ 92%]
    tests/test_xadvanced.py::test_manual_timeout_task FAILED                                                [100%]

    ================================================== FAILURES ===================================================
    ___________________________________________ test_execute_fn_invalid ___________________________________________

    obj = 'gASV3wAAAAAAAACMEmZhaWx1cmVfZXhjZXB0aW9uc5SMF0Z1bmN0aW9uRmFpbGVkRXhjZXB0aW9u\nlJOUKIwFTE9DQUyUjCQ4N2Q0MmRkOC03MjkxLTR...b25hbCBhcmd1bWVudDogJ3gnIHdo\nZW4gZXhlY3V0aW5nIHRhc2sgODdkNDJkZDgtNzI5MS00YmQ3LWE1ZTYtY2NhOTM0MTE4YWUwlE30\nAXSUUpQu\n'

        def deserialize(obj: str):
            """Deserialize a Python object from a base64-encoded string."""
            try :
    >           return dill.loads(codecs.decode(obj.encode(), "base64"))

    tests/serialize.py:24:
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:301: in loads
        return load(file, ignore, **kwds)
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:287: in load
        return Unpickler(file, ignore=ignore, **kwds).load()
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:442: in load
        obj = StockUnpickler.load(self)
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    self = <dill._dill.Unpickler object at 0x10bdad950>, module = 'failure_exceptions'
    name = 'FunctionFailedException'

        def find_class(self, module, name):
            if (module, name) == ('__builtin__', '__main__'):
                return self._main.__dict__ #XXX: above set w/save_module_dict
            elif (module, name) == ('__builtin__', 'NoneType'):
                return type(None) #XXX: special case: NoneType missing
            if module == 'dill.dill': module = 'dill._dill'
    >       return StockUnpickler.find_class(self, module, name)
    E       ModuleNotFoundError: No module named 'failure_exceptions'

    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:432: ModuleNotFoundError

    The above exception was the direct cause of the following exception:

    function_ids = {'bruteforce_password_fn_id': '00a264b8-d382-4937-bbbc-bb2701548164', 'double_fn_id': 'ab7681a2-28e4-4b4a-b8a3-17081f4... 'fibonacci_fn_id': '6237b12f-8f9e-4881-ad6c-a1ee892dfc52', 'no_op_fn_id': '1fc697bb-bb12-46cd-925a-927577f90eec', ...}

        def test_execute_fn_invalid(function_ids):
            """Execute task with missing argument payload
            result should be FunctionFailedException"""
            resp = requests.post(base_url + "execute_function",
                                 json={"function_id": function_ids["double_fn_id"],
                                       "payload": serialize(((), {}))}) #double required one arg, submitting None
            failed_task_id = resp.json().get("task_id")
            time.sleep(5)
            resp = get_result(failed_task_id)

    >       deser_result = deserialize(resp["result"])

    tests/test_webservice_ext.py:222:
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    obj = 'gASV3wAAAAAAAACMEmZhaWx1cmVfZXhjZXB0aW9uc5SMF0Z1bmN0aW9uRmFpbGVkRXhjZXB0aW9u\nlJOUKIwFTE9DQUyUjCQ4N2Q0MmRkOC03MjkxLTR...b25hbCBhcmd1bWVudDogJ3gnIHdo\nZW4gZXhlY3V0aW5nIHRhc2sgODdkNDJkZDgtNzI5MS00YmQ3LWE1ZTYtY2NhOTM0MTE4YWUwlE30\nAXSUUpQu\n'

        def deserialize(obj: str):
            """Deserialize a Python object from a base64-encoded string."""
            try :
                return dill.loads(codecs.decode(obj.encode(), "base64"))
            except Exception as e:
    >           raise DeserializationError(f"Failed to deserialize object: {e}") from e
    E           app.tests.serialize.DeserializationError: Failed to deserialize object: No module named 'failure_exceptions'

    tests/serialize.py:26: DeserializationError
    ________________________________________ test_execute_fn_invalid_kwarg ________________________________________

    obj = 'gASV9gAAAAAAAACMEmZhaWx1cmVfZXhjZXB0aW9uc5SMF0Z1bmN0aW9uRmFpbGVkRXhjZXB0aW9u\nlJOUKIwFTE9DQUyUjCQyYTY2ZDZlZC00OTdmLTR...NpYXRlZCB3aXRoIGEgdmFsdWUgd2hlbiBleGVjdXRpbmcgdGFzayAyYTY2ZDZlZC00OTdmLTRk\nNzctOGE1My1jZGFkYjcwNmNiZmKUTfQBdJRSlC4=\n'

        def deserialize(obj: str):
            """Deserialize a Python object from a base64-encoded string."""
            try :
    >           return dill.loads(codecs.decode(obj.encode(), "base64"))

    tests/serialize.py:24:
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:301: in loads
        return load(file, ignore, **kwds)
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:287: in load
        return Unpickler(file, ignore=ignore, **kwds).load()
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:442: in load
        obj = StockUnpickler.load(self)
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    self = <dill._dill.Unpickler object at 0x10bdae710>, module = 'failure_exceptions'
    name = 'FunctionFailedException'

        def find_class(self, module, name):
            if (module, name) == ('__builtin__', '__main__'):
                return self._main.__dict__ #XXX: above set w/save_module_dict
            elif (module, name) == ('__builtin__', 'NoneType'):
                return type(None) #XXX: special case: NoneType missing
            if module == 'dill.dill': module = 'dill._dill'
    >       return StockUnpickler.find_class(self, module, name)
    E       ModuleNotFoundError: No module named 'failure_exceptions'

    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:432: ModuleNotFoundError

    The above exception was the direct cause of the following exception:

    function_ids = {'bruteforce_password_fn_id': '00a264b8-d382-4937-bbbc-bb2701548164', 'double_fn_id': 'ab7681a2-28e4-4b4a-b8a3-17081f4... 'fibonacci_fn_id': '6237b12f-8f9e-4881-ad6c-a1ee892dfc52', 'no_op_fn_id': '1fc697bb-bb12-46cd-925a-927577f90eec', ...}

        def test_execute_fn_invalid_kwarg(function_ids):
            """Execute task with invalid payload
            result should be FunctionFailedException"""
            resp = requests.post(base_url + "execute_function",
                                 json={"function_id": function_ids["double_fn_id"],
                                       "payload": serialize(((2,),))}) #double required kwargs, submitting None
            failed_task_id = resp.json().get("task_id")
            time.sleep(5)
            resp = get_result(failed_task_id)
    >       deser_result = deserialize(resp["result"])

    tests/test_webservice_ext.py:238:
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    obj = 'gASV9gAAAAAAAACMEmZhaWx1cmVfZXhjZXB0aW9uc5SMF0Z1bmN0aW9uRmFpbGVkRXhjZXB0aW9u\nlJOUKIwFTE9DQUyUjCQyYTY2ZDZlZC00OTdmLTR...NpYXRlZCB3aXRoIGEgdmFsdWUgd2hlbiBleGVjdXRpbmcgdGFzayAyYTY2ZDZlZC00OTdmLTRk\nNzctOGE1My1jZGFkYjcwNmNiZmKUTfQBdJRSlC4=\n'

        def deserialize(obj: str):
            """Deserialize a Python object from a base64-encoded string."""
            try :
                return dill.loads(codecs.decode(obj.encode(), "base64"))
            except Exception as e:
    >           raise DeserializationError(f"Failed to deserialize object: {e}") from e
    E           app.tests.serialize.DeserializationError: Failed to deserialize object: No module named 'failure_exceptions'

    tests/serialize.py:26: DeserializationError
    __________________________________________ test_manual_timeout_task ___________________________________________

    function_ids = None

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
    >       assert resp["status"] == "FAILED", "The task timeout did not hit."
    E       AssertionError: The task timeout did not hit.
    E       assert 'RUNNING' == 'FAILED'
    E
    E         - FAILED
    E         + RUNNING

    tests/test_xadvanced.py:263: AssertionError
    ---------------------------------------------- Captured log call ----------------------------------------------
    WARNING  root:test_xadvanced.py:251 Timedout Task ID : 4fe23f7d-9f32-477f-aa35-908c671f7dd9
    =========================================== short test summary info ===========================================
    FAILED tests/test_webservice_ext.py::test_execute_fn_invalid - app.tests.serialize.DeserializationError: Failed to deserialize object: No module named 'failure_exceptions'
    FAILED tests/test_webservice_ext.py::test_execute_fn_invalid_kwarg - app.tests.serialize.DeserializationError: Failed to deserialize object: No module named 'failure_exceptions'
    FAILED tests/test_xadvanced.py::test_manual_timeout_task - AssertionError: The task timeout did not hit.
    ======================================== 3 failed, 11 passed in 57.16s ========================================


### Pull mode tests

    (mpcs_py3.11) /Users/yadu/src/MPCS52040/project-submissions/project-card_readers/app:>pytest -v tests/
    ============================================= test session starts =============================================
    platform darwin -- Python 3.11.10, pytest-8.3.3, pluggy-1.5.0 -- /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/bin/python
    cachedir: .pytest_cache
    rootdir: /Users/yadu/src/MPCS52040/project-submissions/project-card_readers
    plugins: anyio-4.6.2.post1
    collected 14 items

    tests/test_webservice.py::test_fn_registration_invalid PASSED                                           [  7%]
    tests/test_webservice.py::test_fn_registration PASSED                                                   [ 14%]
    tests/test_webservice.py::test_execute_fn PASSED                                                        [ 21%]
    tests/test_webservice.py::test_roundtrip PASSED                                                         [ 28%]
    tests/test_webservice.py::test_roundtrip_result PASSED                                                  [ 35%]
    tests/test_webservice_ext.py::test_fastapi_register_functions PASSED                                    [ 42%]
    tests/test_webservice_ext.py::test_fastapi_execute_function PASSED                                      [ 50%]
    tests/test_webservice_ext.py::test_fastapi_get_status PASSED                                            [ 57%]
    tests/test_webservice_ext.py::test_fastapi_get_result FAILED                                            [ 64%]
    tests/test_webservice_ext.py::test_fn_registration_invalid PASSED                                       [ 71%]
    tests/test_webservice_ext.py::test_execute_fn_invalid FAILED                                            [ 78%]
    tests/test_webservice_ext.py::test_execute_fn_invalid_kwarg FAILED                                      [ 85%]
    tests/test_xadvanced.py::test_concurrent_tasks PASSED                                                   [ 92%]
    tests/test_xadvanced.py::test_manual_timeout_task FAILED                                                [100%]

    ================================================== FAILURES ===================================================
    ___________________________________________ test_fastapi_get_result ___________________________________________

    obj = 'gASVAwEAAAAAAACMEmZhaWx1cmVfZXhjZXB0aW9uc5SMFldvcmtlckZhaWx1cmVFeGNlcHRpb26U\nk5QojClQVUxMOjY1ZTVjNzc2LWFjZjktNDE3Ny1...IzIGZhaWxlZCBvbiB3b3JrZXIgUFVMTDo2NWU1Yzc3Ni1hY2Y5LTQxNzct\nYWU1OC03NGU3NjBlNTk2MmQgZHVlIHRvIHRpbWVvdXQulE30AXSUUpQu\n'

        def deserialize(obj: str):
            """Deserialize a Python object from a base64-encoded string."""
            try :
    >           return dill.loads(codecs.decode(obj.encode(), "base64"))

    tests/serialize.py:24:
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:301: in loads
        return load(file, ignore, **kwds)
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:287: in load
        return Unpickler(file, ignore=ignore, **kwds).load()
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:442: in load
        obj = StockUnpickler.load(self)
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    self = <dill._dill.Unpickler object at 0x10e4fe850>, module = 'failure_exceptions'
    name = 'WorkerFailureException'

        def find_class(self, module, name):
            if (module, name) == ('__builtin__', '__main__'):
                return self._main.__dict__ #XXX: above set w/save_module_dict
            elif (module, name) == ('__builtin__', 'NoneType'):
                return type(None) #XXX: special case: NoneType missing
            if module == 'dill.dill': module = 'dill._dill'
    >       return StockUnpickler.find_class(self, module, name)
    E       ModuleNotFoundError: No module named 'failure_exceptions'

    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:432: ModuleNotFoundError

    The above exception was the direct cause of the following exception:

    task_ids = {'bruteforce_password': '0532b679-f20b-4230-9850-f1987649e05c', 'double': '53854358-d9d1-4662-b4ca-ae9ecebce84a', 'fibonacci': '152f481b-672b-47e4-882a-2a3a53a112a6', 'no_op': 'c055e739-fe24-4678-b489-580f88afc7fb', ...}

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
    >               check_result(fn_name, task_id, "Slept")

    tests/test_webservice_ext.py:195:
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
    tests/test_webservice_ext.py:180: in check_result
        deser_result = deserialize(result["result"])
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    obj = 'gASVAwEAAAAAAACMEmZhaWx1cmVfZXhjZXB0aW9uc5SMFldvcmtlckZhaWx1cmVFeGNlcHRpb26U\nk5QojClQVUxMOjY1ZTVjNzc2LWFjZjktNDE3Ny1...IzIGZhaWxlZCBvbiB3b3JrZXIgUFVMTDo2NWU1Yzc3Ni1hY2Y5LTQxNzct\nYWU1OC03NGU3NjBlNTk2MmQgZHVlIHRvIHRpbWVvdXQulE30AXSUUpQu\n'

        def deserialize(obj: str):
            """Deserialize a Python object from a base64-encoded string."""
            try :
                return dill.loads(codecs.decode(obj.encode(), "base64"))
            except Exception as e:
    >           raise DeserializationError(f"Failed to deserialize object: {e}") from e
    E           app.tests.serialize.DeserializationError: Failed to deserialize object: No module named 'failure_exceptions'

    tests/serialize.py:26: DeserializationError
    ---------------------------------------------- Captured log call ----------------------------------------------
    WARNING  root:test_webservice_ext.py:173
     fn_name : no_op
     task_id: c055e739-fe24-4678-b489-580f88afc7fb
    WARNING  root:test_webservice_ext.py:183
     -> COMPLETED. Result: DONE
    WARNING  root:test_webservice_ext.py:173
     fn_name : double
     task_id: 53854358-d9d1-4662-b4ca-ae9ecebce84a
    WARNING  root:test_webservice_ext.py:183
     -> COMPLETED. Result: 4
    WARNING  root:test_webservice_ext.py:173
     fn_name : sleep_1s
     task_id: 34098ea3-5bf8-46c3-b545-0cfc2fdb4e23
    ___________________________________________ test_execute_fn_invalid ___________________________________________

    obj = 'gASV4QAAAAAAAACMEmZhaWx1cmVfZXhjZXB0aW9uc5SMF0Z1bmN0aW9uRmFpbGVkRXhjZXB0aW9u\nlJOUKIwpUFVMTDo2NWU1Yzc3Ni1hY2Y5LTQxNzc...cm9jZXNzaW5nIHRhc2sgcmVz\ndWx0OmRvdWJsZSgpIG1pc3NpbmcgMSByZXF1aXJlZCBwb3NpdGlvbmFsIGFyZ3VtZW50OiAneCeU\nTfQBdJRSlC4=\n'

        def deserialize(obj: str):
            """Deserialize a Python object from a base64-encoded string."""
            try :
    >           return dill.loads(codecs.decode(obj.encode(), "base64"))

    tests/serialize.py:24:
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:301: in loads
        return load(file, ignore, **kwds)
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:287: in load
        return Unpickler(file, ignore=ignore, **kwds).load()
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:442: in load
        obj = StockUnpickler.load(self)
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    self = <dill._dill.Unpickler object at 0x10e4fde50>, module = 'failure_exceptions'
    name = 'FunctionFailedException'

        def find_class(self, module, name):
            if (module, name) == ('__builtin__', '__main__'):
                return self._main.__dict__ #XXX: above set w/save_module_dict
            elif (module, name) == ('__builtin__', 'NoneType'):
                return type(None) #XXX: special case: NoneType missing
            if module == 'dill.dill': module = 'dill._dill'
    >       return StockUnpickler.find_class(self, module, name)
    E       ModuleNotFoundError: No module named 'failure_exceptions'

    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:432: ModuleNotFoundError

    The above exception was the direct cause of the following exception:

    function_ids = {'bruteforce_password_fn_id': 'cae9a4ee-3677-4064-bc5a-546eb53836dc', 'double_fn_id': 'b5bfd6dd-4214-44fb-b078-a71f16e... 'fibonacci_fn_id': 'fa023c12-5be5-4846-92d1-799099d8866c', 'no_op_fn_id': '2a7157e7-6032-4070-8edd-86da8d66e3dc', ...}

        def test_execute_fn_invalid(function_ids):
            """Execute task with missing argument payload
            result should be FunctionFailedException"""
            resp = requests.post(base_url + "execute_function",
                                 json={"function_id": function_ids["double_fn_id"],
                                       "payload": serialize(((), {}))}) #double required one arg, submitting None
            failed_task_id = resp.json().get("task_id")
            time.sleep(5)
            resp = get_result(failed_task_id)

    >       deser_result = deserialize(resp["result"])

    tests/test_webservice_ext.py:222:
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    obj = 'gASV4QAAAAAAAACMEmZhaWx1cmVfZXhjZXB0aW9uc5SMF0Z1bmN0aW9uRmFpbGVkRXhjZXB0aW9u\nlJOUKIwpUFVMTDo2NWU1Yzc3Ni1hY2Y5LTQxNzc...cm9jZXNzaW5nIHRhc2sgcmVz\ndWx0OmRvdWJsZSgpIG1pc3NpbmcgMSByZXF1aXJlZCBwb3NpdGlvbmFsIGFyZ3VtZW50OiAneCeU\nTfQBdJRSlC4=\n'

        def deserialize(obj: str):
            """Deserialize a Python object from a base64-encoded string."""
            try :
                return dill.loads(codecs.decode(obj.encode(), "base64"))
            except Exception as e:
    >           raise DeserializationError(f"Failed to deserialize object: {e}") from e
    E           app.tests.serialize.DeserializationError: Failed to deserialize object: No module named 'failure_exceptions'

    tests/serialize.py:26: DeserializationError
    ________________________________________ test_execute_fn_invalid_kwarg ________________________________________

    obj = 'gASVwAAAAAAAAACMEmZhaWx1cmVfZXhjZXB0aW9uc5SMF0Z1bmN0aW9uRmFpbGVkRXhjZXB0aW9u\nlJOUKIwpUFVMTDo2NWU1Yzc3Ni1hY2Y5LTQxNzc...FmLTQyNzQtODVhYS1iZWM1ZTNmOGMxYzSUjDBFcnJvciBnZXR0aW5nIHRhc2sgcGFyYW1z\nOmFyZ3Mgb3Iga3dhcmdzIG1pc3NpbmeUTfQBdJRSlC4=\n'

        def deserialize(obj: str):
            """Deserialize a Python object from a base64-encoded string."""
            try :
    >           return dill.loads(codecs.decode(obj.encode(), "base64"))

    tests/serialize.py:24:
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:301: in loads
        return load(file, ignore, **kwds)
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:287: in load
        return Unpickler(file, ignore=ignore, **kwds).load()
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:442: in load
        obj = StockUnpickler.load(self)
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    self = <dill._dill.Unpickler object at 0x10e4ff250>, module = 'failure_exceptions'
    name = 'FunctionFailedException'

        def find_class(self, module, name):
            if (module, name) == ('__builtin__', '__main__'):
                return self._main.__dict__ #XXX: above set w/save_module_dict
            elif (module, name) == ('__builtin__', 'NoneType'):
                return type(None) #XXX: special case: NoneType missing
            if module == 'dill.dill': module = 'dill._dill'
    >       return StockUnpickler.find_class(self, module, name)
    E       ModuleNotFoundError: No module named 'failure_exceptions'

    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:432: ModuleNotFoundError

    The above exception was the direct cause of the following exception:

    function_ids = {'bruteforce_password_fn_id': 'cae9a4ee-3677-4064-bc5a-546eb53836dc', 'double_fn_id': 'b5bfd6dd-4214-44fb-b078-a71f16e... 'fibonacci_fn_id': 'fa023c12-5be5-4846-92d1-799099d8866c', 'no_op_fn_id': '2a7157e7-6032-4070-8edd-86da8d66e3dc', ...}

        def test_execute_fn_invalid_kwarg(function_ids):
            """Execute task with invalid payload
            result should be FunctionFailedException"""
            resp = requests.post(base_url + "execute_function",
                                 json={"function_id": function_ids["double_fn_id"],
                                       "payload": serialize(((2,),))}) #double required kwargs, submitting None
            failed_task_id = resp.json().get("task_id")
            time.sleep(5)
            resp = get_result(failed_task_id)
    >       deser_result = deserialize(resp["result"])

    tests/test_webservice_ext.py:238:
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    obj = 'gASVwAAAAAAAAACMEmZhaWx1cmVfZXhjZXB0aW9uc5SMF0Z1bmN0aW9uRmFpbGVkRXhjZXB0aW9u\nlJOUKIwpUFVMTDo2NWU1Yzc3Ni1hY2Y5LTQxNzc...FmLTQyNzQtODVhYS1iZWM1ZTNmOGMxYzSUjDBFcnJvciBnZXR0aW5nIHRhc2sgcGFyYW1z\nOmFyZ3Mgb3Iga3dhcmdzIG1pc3NpbmeUTfQBdJRSlC4=\n'

        def deserialize(obj: str):
            """Deserialize a Python object from a base64-encoded string."""
            try :
                return dill.loads(codecs.decode(obj.encode(), "base64"))
            except Exception as e:
    >           raise DeserializationError(f"Failed to deserialize object: {e}") from e
    E           app.tests.serialize.DeserializationError: Failed to deserialize object: No module named 'failure_exceptions'

    tests/serialize.py:26: DeserializationError
    __________________________________________ test_manual_timeout_task ___________________________________________

    obj = 'gASVAwEAAAAAAACMEmZhaWx1cmVfZXhjZXB0aW9uc5SMFldvcmtlckZhaWx1cmVFeGNlcHRpb26U\nk5QojClQVUxMOjY1ZTVjNzc2LWFjZjktNDE3Ny1...MzIGZhaWxlZCBvbiB3b3JrZXIgUFVMTDo2NWU1Yzc3Ni1hY2Y5LTQxNzct\nYWU1OC03NGU3NjBlNTk2MmQgZHVlIHRvIHRpbWVvdXQulE30AXSUUpQu\n'

        def deserialize(obj: str):
            """Deserialize a Python object from a base64-encoded string."""
            try :
    >           return dill.loads(codecs.decode(obj.encode(), "base64"))

    tests/serialize.py:24:
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:301: in loads
        return load(file, ignore, **kwds)
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:287: in load
        return Unpickler(file, ignore=ignore, **kwds).load()
    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:442: in load
        obj = StockUnpickler.load(self)
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    self = <dill._dill.Unpickler object at 0x10e4ff610>, module = 'failure_exceptions'
    name = 'WorkerFailureException'

        def find_class(self, module, name):
            if (module, name) == ('__builtin__', '__main__'):
                return self._main.__dict__ #XXX: above set w/save_module_dict
            elif (module, name) == ('__builtin__', 'NoneType'):
                return type(None) #XXX: special case: NoneType missing
            if module == 'dill.dill': module = 'dill._dill'
    >       return StockUnpickler.find_class(self, module, name)
    E       ModuleNotFoundError: No module named 'failure_exceptions'

    /Users/yadu/opt/anaconda3/envs/mpcs_py3.11/lib/python3.11/site-packages/dill/_dill.py:432: ModuleNotFoundError

    The above exception was the direct cause of the following exception:

    function_ids = None

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

    >       result = deserialize(resp["result"])

    tests/test_xadvanced.py:265:
    _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    obj = 'gASVAwEAAAAAAACMEmZhaWx1cmVfZXhjZXB0aW9uc5SMFldvcmtlckZhaWx1cmVFeGNlcHRpb26U\nk5QojClQVUxMOjY1ZTVjNzc2LWFjZjktNDE3Ny1...MzIGZhaWxlZCBvbiB3b3JrZXIgUFVMTDo2NWU1Yzc3Ni1hY2Y5LTQxNzct\nYWU1OC03NGU3NjBlNTk2MmQgZHVlIHRvIHRpbWVvdXQulE30AXSUUpQu\n'

        def deserialize(obj: str):
            """Deserialize a Python object from a base64-encoded string."""
            try :
                return dill.loads(codecs.decode(obj.encode(), "base64"))
            except Exception as e:
    >           raise DeserializationError(f"Failed to deserialize object: {e}") from e
    E           app.tests.serialize.DeserializationError: Failed to deserialize object: No module named 'failure_exceptions'

    tests/serialize.py:26: DeserializationError
    ---------------------------------------------- Captured log call ----------------------------------------------
    WARNING  root:test_xadvanced.py:251 Timedout Task ID : f58ee58a-5c27-48b4-82b2-07d0b0a91c33
    =========================================== short test summary info ===========================================
    FAILED tests/test_webservice_ext.py::test_fastapi_get_result - app.tests.serialize.DeserializationError: Failed to deserialize object: No module named 'failure_exceptions'
    FAILED tests/test_webservice_ext.py::test_execute_fn_invalid - app.tests.serialize.DeserializationError: Failed to deserialize object: No module named 'failure_exceptions'
    FAILED tests/test_webservice_ext.py::test_execute_fn_invalid_kwarg - app.tests.serialize.DeserializationError: Failed to deserialize object: No module named 'failure_exceptions'
    FAILED tests/test_xadvanced.py::test_manual_timeout_task - app.tests.serialize.DeserializationError: Failed to deserialize object: No module named 'failure_exceptions'
    =================================== 4 failed, 10 passed in 88.06s (0:01:28) ===================================
    (mpcs_py3.11) /Users/yadu/src/MPCS52040/project-submissions/project-card_readers/app:>~


    ### Push mode

    Same failures as pull mode