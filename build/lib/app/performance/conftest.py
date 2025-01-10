def pytest_addoption(parser):
    parser.addoption(
        "--workers", action="store", default="1", help="Number of workers for the weak scaling test"
    )
    parser.addoption(
        "--optype", action="store", default="sleep", help="Type of task to test with(noop, sleep, heavy)"
    )
    parser.addoption(
    "--mode", action="store", default="local", help="Dispatcher mode(local, push, pull)"
    )

import pytest

@pytest.fixture
def workers(request):
    return int(request.config.getoption("--workers"))

@pytest.fixture
def optype(request):
    return str(request.config.getoption("--optype"))

@pytest.fixture
def mode(request):
    return str(request.config.getoption("--mode"))