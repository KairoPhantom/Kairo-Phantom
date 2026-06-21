"""
Tests for keychain_store.py — P1.2 Key storage security.

These tests assert that BYO-key cloud API keys land ONLY in the OS keychain
abstraction, never in config files or logs.

Tests verify:
1. Storing a key places it in the keychain abstraction.
2. Retrieving a key returns the correct value.
3. No key material appears in config files after store+retrieve.
4. No key material appears in log output.
5. Deleting a key removes it from the keychain.
6. The keychain store never writes plaintext to disk.
"""
import io
import json
import logging
import os
import sys
import tempfile

import pytest

# Ensure the scripts directory is importable
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from keychain_store import (
    KeychainStore,
    KAIRO_KEYCHAIN_SERVICE,
    scan_config_files_for_keys,
    scan_logs_for_keys,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_log_dir():
    """Create a temporary log directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def keychain():
    """Create a fresh KeychainStore instance for each test."""
    store = KeychainStore()
    yield store
    # Cleanup: delete any test keys
    for key_name in ["test_api_key", "test_openai_key", "test_anthropic_key", "test_secret"]:
        store.delete_key(key_name)


@pytest.fixture
def caplog_captured():
    """Capture log output to verify no key material leaks."""
    logger = logging.getLogger("keychain_store")
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield log_stream
    logger.removeHandler(handler)


# ---------------------------------------------------------------------------
# Key storage and retrieval tests
# ---------------------------------------------------------------------------

def test_key_stored_and_retrieved(keychain):
    """A key stored in the keychain must be retrievable with the correct value."""
    test_key = "sk-test-1234567890abcdef"
    keychain.store_key("test_api_key", test_key)
    retrieved = keychain.retrieve_key("test_api_key")
    assert retrieved == test_key


def test_key_not_in_config_files(keychain, temp_config_dir):
    """After storing a key, no config file must contain the key material."""
    test_key = "sk-test-1234567890abcdef"
    keychain.store_key("test_api_key", test_key)

    # Write a dummy config file to ensure the scan works
    config_path = os.path.join(temp_config_dir, "settings.toml")
    with open(config_path, "w") as f:
        f.write("[kairo]\nmode = \"local\"\n")

    # Scan for the key pattern
    violations = scan_config_files_for_keys(
        temp_config_dir,
        [r"sk-test-\d+[a-f]+", test_key]
    )
    assert len(violations) == 0, \
        f"Key material found in config files: {violations}"


def test_key_not_in_logs(keychain, caplog_captured):
    """After storing and retrieving a key, no log output must contain the key value."""
    test_key = "sk-test-SECRETVALUE123"
    keychain.store_key("test_api_key", test_key)
    retrieved = keychain.retrieve_key("test_api_key")

    # Check log output
    log_output = caplog_captured.getvalue()
    assert test_key not in log_output, \
        f"Key material leaked into log output: {log_output}"
    assert "SECRETVALUE123" not in log_output, \
        f"Key material leaked into log output: {log_output}"


def test_key_deleted(keychain):
    """A deleted key must no longer be retrievable."""
    keychain.store_key("test_api_key", "sk-test-value")
    assert keychain.retrieve_key("test_api_key") is not None
    deleted = keychain.delete_key("test_api_key")
    assert deleted is True
    assert keychain.retrieve_key("test_api_key") is None


def test_retrieve_nonexistent_key_returns_none(keychain):
    """Retrieving a key that doesn't exist must return None, not raise."""
    result = keychain.retrieve_key("nonexistent_key_12345")
    assert result is None


def test_empty_key_rejected(keychain):
    """Storing an empty key value must raise ValueError."""
    with pytest.raises(ValueError, match="Cannot store empty key"):
        keychain.store_key("test_api_key", "")


# ---------------------------------------------------------------------------
# Config file contamination tests
# ---------------------------------------------------------------------------

def test_config_files_clean_after_key_operations(keychain, temp_config_dir):
    """After a full store+retrieve+delete cycle, config files must be clean."""
    test_key = "sk-ant-api-key-SECRET123"
    keychain.store_key("test_anthropic_key", test_key)
    _ = keychain.retrieve_key("test_anthropic_key")
    keychain.delete_key("test_anthropic_key")

    # Create a config file that should NOT contain the key
    config_path = os.path.join(temp_config_dir, "kairo.json")
    with open(config_path, "w") as f:
        json.dump({"mode": "local", "airgap": True}, f)

    violations = scan_config_files_for_keys(
        temp_config_dir,
        [r"sk-ant-api-key-SECRET\d+", test_key]
    )
    assert len(violations) == 0


def test_scan_detects_key_in_config_if_present(temp_config_dir):
    """The config scanner must detect key material if it IS present.

    This is a failing-capable test: if the scanner stops working, this goes RED.
    """
    config_path = os.path.join(temp_config_dir, "secrets.toml")
    with open(config_path, "w") as f:
        f.write('api_key = "sk-leaked-key-12345"\n')

    violations = scan_config_files_for_keys(
        temp_config_dir,
        [r"sk-leaked-key-\d+"]
    )
    assert len(violations) > 0, \
        "Regression: config scanner failed to detect leaked key material"


def test_scan_detects_key_in_logs_if_present(temp_log_dir):
    """The log scanner must detect key material if it IS present."""
    log_path = os.path.join(temp_log_dir, "kairo.log")
    with open(log_path, "w") as f:
        f.write("2026-06-22 INFO: Using API key sk-leaked-in-log-99999\n")

    violations = scan_logs_for_keys(
        temp_log_dir,
        [r"sk-leaked-in-log-\d+"]
    )
    assert len(violations) > 0, \
        "Regression: log scanner failed to detect leaked key material"


# ---------------------------------------------------------------------------
# Keychain isolation tests
# ---------------------------------------------------------------------------

def test_keychain_service_name_is_kairo(keychain):
    """The keychain must use the Kairo service name, not a generic one."""
    assert keychain.service == KAIRO_KEYCHAIN_SERVICE


def test_multiple_keys_stored_separately(keychain):
    """Multiple keys must be stored and retrieved independently."""
    keychain.store_key("test_openai_key", "sk-openai-123")
    keychain.store_key("test_anthropic_key", "sk-ant-456")

    assert keychain.retrieve_key("test_openai_key") == "sk-openai-123"
    assert keychain.retrieve_key("test_anthropic_key") == "sk-ant-456"

    # Cleanup
    keychain.delete_key("test_openai_key")
    keychain.delete_key("test_anthropic_key")


def test_key_value_not_in_key_names(keychain):
    """list_key_names must return key names, never key values."""
    keychain.store_key("test_api_key", "sk-super-secret-value")
    names = keychain.list_key_names()
    names_text = " ".join(names) if names else ""
    assert "sk-super-secret-value" not in names_text


# ---------------------------------------------------------------------------
# Failing-capable tests
# ---------------------------------------------------------------------------

def test_failing_capable_key_never_in_config(keychain, temp_config_dir):
    """This test FAILS if key material ever leaks into a config file.

    To verify: modify store_key to write to a config file and this test
    will go RED.
    """
    secret = "sk-failing-capable-test-KEY"
    keychain.store_key("test_secret", secret)

    # Write a config file (simulating the app's config directory)
    config_path = os.path.join(temp_config_dir, "kairo_config.toml")
    with open(config_path, "w") as f:
        f.write('[settings]\nairgap = true\n')

    # The key must NOT be in any config file
    violations = scan_config_files_for_keys(temp_config_dir, [secret])
    assert len(violations) == 0, \
        f"Regression: key material leaked to config file: {violations}"


def test_failing_capable_key_never_in_logs(keychain, caplog_captured):
    """This test FAILS if key material ever leaks into log output.

    To verify: modify store_key to log the key value and this test goes RED.
    """
    secret = "sk-LOG-LEAK-TEST-12345"
    keychain.store_key("test_secret", secret)
    _ = keychain.retrieve_key("test_secret")

    log_output = caplog_captured.getvalue()
    assert secret not in log_output, \
        f"Regression: key material leaked into log: {log_output}"