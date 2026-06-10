"""Tests for crash reporter module."""
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import sidecar.crash_reporter as crash_module
from sidecar.crash_reporter import (
    install_crash_handler, _write_crash_report, write_manual_crash, _crash_handler
)


def test_install_crash_handler():
    original = sys.excepthook
    install_crash_handler()
    assert sys.excepthook is not original
    # Restore
    sys.excepthook = original


def test_write_crash_report(tmp_path):
    with patch.object(crash_module, "CRASH_DIR", tmp_path):
        try:
            raise ValueError("test error")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            crash_file = _write_crash_report(exc_type, exc_value, exc_tb)
    assert crash_file.exists()
    data = json.loads(crash_file.read_text())
    assert data["exception"]["type"] == "ValueError"
    assert data["exception"]["message"] == "test error"
    assert "platform" in data
    assert data["version"] == "3.9.0"
    # Confirm no PII fields
    assert "user_text" not in data
    assert "document_content" not in data


def test_write_crash_report_traceback_is_list(tmp_path):
    with patch.object(crash_module, "CRASH_DIR", tmp_path):
        try:
            raise RuntimeError("traceback test")
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            crash_file = _write_crash_report(exc_type, exc_value, exc_tb)
    data = json.loads(crash_file.read_text())
    assert isinstance(data["exception"]["traceback"], list)


def test_write_manual_crash(tmp_path):
    with patch.object(crash_module, "CRASH_DIR", tmp_path):
        crash_file = write_manual_crash("manual error", extra={"context": "test"})
    assert crash_file.exists()
    data = json.loads(crash_file.read_text())
    assert data["message"] == "manual error"
    assert data["type"] == "manual"
    assert data["extra"]["context"] == "test"


def test_crash_handler_writes_file(tmp_path, capsys):
    with patch.object(crash_module, "CRASH_DIR", tmp_path):
        try:
            raise KeyError("missing_key")
        except KeyError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            with patch("sys.__excepthook__", lambda *a: None):
                _crash_handler(exc_type, exc_value, exc_tb)
    files = list(tmp_path.glob("crash_*.json"))
    assert len(files) == 1
    captured = capsys.readouterr()
    assert "Kairo Phantom" in captured.err
    assert "github.com" in captured.err
