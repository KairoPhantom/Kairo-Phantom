import pytest

def pytest_runtest_setup(item):
    # Enforce no skipped or xfailed tests at runtime via markers
    if item.get_closest_marker("skip"):
        pytest.fail("Skipped tests are strictly forbidden!", pytrace=False)
    if item.get_closest_marker("skipif"):
        pytest.fail("Conditional skipped tests (skipif) are strictly forbidden!", pytrace=False)
    if item.get_closest_marker("xfail"):
        pytest.fail("Xfailed tests are strictly forbidden!", pytrace=False)

def pytest_runtest_logreport(report):
    # Enforce no dynamic runtime skips or xfails
    if report.outcome == "skipped":
        raise pytest.UsageError(f"Skipped tests are strictly forbidden at runtime: {report.nodeid}")
    if hasattr(report, "wasxfail"):
        raise pytest.UsageError(f"Xfailed tests are strictly forbidden at runtime: {report.nodeid}")

@pytest.fixture
def anyio_backend():
    return 'asyncio'
