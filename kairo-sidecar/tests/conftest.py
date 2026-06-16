import sys
import os
import pytest

# Setup pathing
_conftest_dir = os.path.dirname(os.path.abspath(__file__))
_sidecar_root = os.path.dirname(_conftest_dir)
if _sidecar_root not in sys.path:
    sys.path.insert(0, _sidecar_root)
if os.path.join(_sidecar_root, "sidecar") not in sys.path:
    sys.path.insert(0, os.path.join(_sidecar_root, "sidecar"))


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
