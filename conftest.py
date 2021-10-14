import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--runvax", action="store_true", default=False, help="run vax tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "vax: mark test as including cities with vaxxed people")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runvax"):
        # --runvax given in cli: do not skip slow tests
        return
    skip_vaxxed = pytest.mark.skip(reason="need --runvax option to run")
    for item in items:
        if "vax" in item.keywords:
            item.add_marker(skip_vaxxed)
            
