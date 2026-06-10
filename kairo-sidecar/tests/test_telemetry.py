"""Tests for opt-in telemetry module."""
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import sidecar.telemetry as telemetry_module
from sidecar.telemetry import is_opted_in, record_operation, get_summary


def _write_config(tmp_path: Path, enabled: bool):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"telemetry_enabled": enabled}))
    return config_file


def test_is_opted_in_false_by_default(tmp_path):
    with patch.object(telemetry_module, "CONFIG_FILE", tmp_path / "config.json"):
        assert is_opted_in() is False


def test_is_opted_in_true(tmp_path):
    _write_config(tmp_path, True)
    with patch.object(telemetry_module, "CONFIG_FILE", tmp_path / "config.json"):
        assert is_opted_in() is True


def test_record_operation_no_op_when_not_opted_in(tmp_path):
    tel_file = tmp_path / "telemetry.jsonl"
    with patch.object(telemetry_module, "CONFIG_FILE", tmp_path / "no_config.json"), \
         patch.object(telemetry_module, "TELEMETRY_FILE", tel_file):
        record_operation("word", 123.4)
    assert not tel_file.exists()


def test_record_operation_writes_when_opted_in(tmp_path):
    _write_config(tmp_path, True)
    tel_file = tmp_path / "telemetry.jsonl"
    with patch.object(telemetry_module, "CONFIG_FILE", tmp_path / "config.json"), \
         patch.object(telemetry_module, "TELEMETRY_FILE", tel_file):
        record_operation("word", 123.4, success=True)
        record_operation("excel", 456.7, success=False)
    assert tel_file.exists()
    lines = tel_file.read_text().splitlines()
    assert len(lines) == 2
    e1 = json.loads(lines[0])
    assert e1["domain"] == "word"
    assert e1["latency_ms"] == 123.4
    assert e1["success"] is True
    e2 = json.loads(lines[1])
    assert e2["domain"] == "excel"
    assert e2["success"] is False


def test_get_summary_empty(tmp_path):
    tel_file = tmp_path / "telemetry.jsonl"
    with patch.object(telemetry_module, "TELEMETRY_FILE", tel_file):
        summary = get_summary()
    assert summary["operations"] == 0
    assert summary["domains"] == {}
    assert summary["avg_latency_ms"] == 0


def test_get_summary_with_data(tmp_path):
    _write_config(tmp_path, True)
    tel_file = tmp_path / "telemetry.jsonl"
    with patch.object(telemetry_module, "CONFIG_FILE", tmp_path / "config.json"), \
         patch.object(telemetry_module, "TELEMETRY_FILE", tel_file):
        record_operation("word", 100.0)
        record_operation("word", 200.0)
        record_operation("excel", 300.0)
        summary = get_summary()
    assert summary["operations"] == 3
    assert summary["domains"]["word"] == 2
    assert summary["domains"]["excel"] == 1
    assert summary["avg_latency_ms"] == 200.0
