"""Tests for auto-update module."""
import sys
import os
import json
import threading
from unittest.mock import patch, MagicMock
from io import BytesIO
from urllib import error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sidecar.updater import check_for_update, _is_newer, check_for_update_async, CURRENT_VERSION


def test_is_newer_true():
    assert _is_newer("4.0.0", "3.9.0") is True


def test_is_newer_false_equal():
    assert _is_newer("3.9.0", "3.9.0") is False


def test_is_newer_false_older():
    assert _is_newer("3.8.0", "3.9.0") is False


def test_is_newer_patch():
    assert _is_newer("3.9.1", "3.9.0") is True


def _make_mock_response(tag_name: str, html_url: str = "https://github.com/test/release"):
    """Create a mock urllib response."""
    data = json.dumps({"tag_name": tag_name, "html_url": html_url}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = data
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_check_for_update_newer_available():
    """Returns (version, url) when a newer version exists."""
    with patch("sidecar.updater.request.urlopen", return_value=_make_mock_response("v4.0.0")):
        result = check_for_update()
    assert result is not None
    assert result[0] == "4.0.0"
    assert "github.com" in result[1]


def test_check_for_update_same_version():
    """Returns None when latest == current."""
    with patch("sidecar.updater.request.urlopen",
               return_value=_make_mock_response(f"v{CURRENT_VERSION}")):
        result = check_for_update()
    assert result is None


def test_check_for_update_older_version():
    """Returns None when latest < current."""
    with patch("sidecar.updater.request.urlopen",
               return_value=_make_mock_response("v1.0.0")):
        result = check_for_update()
    assert result is None


def test_check_for_update_network_error():
    """Returns None when network is unavailable."""
    with patch("sidecar.updater.request.urlopen",
               side_effect=error.URLError("Network unreachable")):
        result = check_for_update()
    assert result is None


def test_check_for_update_malformed_response():
    """Returns None when response JSON is malformed."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"not json"
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("sidecar.updater.request.urlopen", return_value=mock_resp):
        result = check_for_update()
    assert result is None


def test_check_for_update_async():
    """Async variant calls callback when update is available."""
    results = []
    done = threading.Event()

    def cb(r):
        results.append(r)
        done.set()

    with patch("sidecar.updater.request.urlopen", return_value=_make_mock_response("v4.0.0")):
        check_for_update_async(cb)
        done.wait(timeout=5)

    assert len(results) == 1
    assert results[0][0] == "4.0.0"
