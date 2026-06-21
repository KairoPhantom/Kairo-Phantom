"""
Kairo Phantom — Installer Smoke Tests (P2.1)

Verifies that installer configuration files are valid and complete:
- ISS file (Inno Setup) has required fields
- Info.plist (macOS) has required keys
- winget manifest has required fields
- config-template.toml is valid
- Modelfile has required directives

No mocks — these tests parse the real installer files from the repo.
"""
from __future__ import annotations

import pathlib
import plistlib
import re
import xml.etree.ElementTree as ET

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
INSTALLER_DIR = REPO_ROOT / "installer"


# ---------------------------------------------------------------------------
# ISS (Inno Setup) validation
# ---------------------------------------------------------------------------
def test_iss_file_exists():
    """The Inno Setup .iss file must exist."""
    iss_path = INSTALLER_DIR / "KairoSetup.iss"
    assert iss_path.exists(), f"Missing ISS file: {iss_path}"


def test_iss_has_required_setup_fields():
    """The ISS file must define all required [Setup] fields."""
    iss_path = INSTALLER_DIR / "KairoSetup.iss"
    content = iss_path.read_text(encoding="utf-8")

    required_fields = [
        "AppName",
        "AppVersion",
        "AppPublisher",
        "AppPublisherURL",
        "DefaultDirName",
        "DefaultGroupName",
        "OutputDir",
        "OutputBaseFilename",
        "Compression",
        "PrivilegesRequired",
    ]
    for field in required_fields:
        assert field in content, f"ISS missing required field: {field}"


def test_iss_has_app_id():
    """The ISS file must have a unique AppId GUID."""
    iss_path = INSTALLER_DIR / "KairoSetup.iss"
    content = iss_path.read_text(encoding="utf-8")
    # AppId should be a GUID in braces
    match = re.search(r"AppId=\{\{([0-9A-Fa-f-]+)\}", content)
    assert match, "ISS missing AppId GUID"


def test_iss_has_files_section():
    """The ISS file must have a [Files] section with source entries."""
    iss_path = INSTALLER_DIR / "KairoSetup.iss"
    content = iss_path.read_text(encoding="utf-8")
    assert "[Files]" in content, "ISS missing [Files] section"
    # Must reference the main binary
    assert "kairo-phantom.exe" in content, "ISS missing main binary reference"
    # Must reference the Python sidecar
    assert "kairo-sidecar" in content, "ISS missing Python sidecar reference"


def test_iss_has_icons_section():
    """The ISS file must have an [Icons] section for shortcuts."""
    iss_path = INSTALLER_DIR / "KairoSetup.iss"
    content = iss_path.read_text(encoding="utf-8")
    assert "[Icons]" in content, "ISS missing [Icons] section"


def test_iss_bundles_sidecar():
    """The ISS file must bundle the Python sidecar (no separate install step)."""
    iss_path = INSTALLER_DIR / "KairoSetup.iss"
    content = iss_path.read_text(encoding="utf-8")
    # The sidecar must be included in [Files]
    assert "kairo-sidecar" in content, "ISS does not bundle Python sidecar"
    # Must create venv during install
    assert "venv" in content.lower(), "ISS does not bootstrap sidecar venv"


# ---------------------------------------------------------------------------
# Info.plist (macOS) validation
# ---------------------------------------------------------------------------
def test_info_plist_exists():
    """The macOS Info.plist must exist."""
    plist_path = INSTALLER_DIR / "macos" / "Info.plist"
    assert plist_path.exists(), f"Missing Info.plist: {plist_path}"


def test_info_plist_is_valid_xml():
    """The Info.plist must be valid XML."""
    plist_path = INSTALLER_DIR / "macos" / "Info.plist"
    content = plist_path.read_text(encoding="utf-8")
    # Should parse as XML without error
    ET.fromstring(content)


def test_info_plist_has_required_keys():
    """The Info.plist must have all required macOS app keys."""
    plist_path = INSTALLER_DIR / "macos" / "Info.plist"
    with open(plist_path, "rb") as f:
        plist_data = plistlib.load(f)

    required_keys = [
        "CFBundleName",
        "CFBundleDisplayName",
        "CFBundleIdentifier",
        "CFBundleVersion",
        "CFBundleShortVersionString",
        "CFBundleExecutable",
        "CFBundlePackageType",
        "LSMinimumSystemVersion",
        "NSHighResolutionCapable",
    ]
    for key in required_keys:
        assert key in plist_data, f"Info.plist missing required key: {key}"


def test_info_plist_has_accessibility_description():
    """The Info.plist must have NSAccessibilityUsageDescription."""
    plist_path = INSTALLER_DIR / "macos" / "Info.plist"
    with open(plist_path, "rb") as f:
        plist_data = plistlib.load(f)
    assert "NSAccessibilityUsageDescription" in plist_data, \
        "Info.plist missing NSAccessibilityUsageDescription"
    desc = plist_data["NSAccessibilityUsageDescription"]
    assert len(desc) > 20, "NSAccessibilityUsageDescription too short"


def test_info_plist_bundle_id_is_valid():
    """The bundle identifier must follow reverse-DNS convention."""
    plist_path = INSTALLER_DIR / "macos" / "Info.plist"
    with open(plist_path, "rb") as f:
        plist_data = plistlib.load(f)
    bundle_id = plist_data["CFBundleIdentifier"]
    assert re.match(r"^[a-z0-9-]+\.[a-z0-9-]+\.[a-z0-9-]+$", bundle_id), \
        f"Invalid bundle identifier: {bundle_id}"


# ---------------------------------------------------------------------------
# winget manifest validation
# ---------------------------------------------------------------------------
def test_winget_manifest_exists():
    """The winget manifest must exist."""
    manifest_path = INSTALLER_DIR / "winget" / "kairo-phantom.yaml"
    assert manifest_path.exists(), f"Missing winget manifest: {manifest_path}"


def test_winget_manifest_has_required_fields():
    """The winget manifest must have all required fields."""
    manifest_path = INSTALLER_DIR / "winget" / "kairo-phantom.yaml"
    content = manifest_path.read_text(encoding="utf-8")

    required_fields = [
        "PackageIdentifier",
        "PackageVersion",
        "PackageName",
        "Publisher",
        "License",
        "InstallerType",
        "InstallerUrl",
        "InstallerSha256",
        "ManifestType",
        "ManifestVersion",
    ]
    for field in required_fields:
        assert field in content, f"winget manifest missing required field: {field}"


def test_winget_manifest_installer_sha256_is_valid():
    """The winget manifest InstallerSha256 must be a valid 64-char hex string."""
    manifest_path = INSTALLER_DIR / "winget" / "kairo-phantom.yaml"
    content = manifest_path.read_text(encoding="utf-8")
    match = re.search(r"InstallerSha256:\s*([0-9a-fA-F]{64})", content)
    assert match, "winget manifest InstallerSha256 is not a valid 64-char hex string"


def test_winget_manifest_license_is_mit():
    """The winget manifest must specify MIT license."""
    manifest_path = INSTALLER_DIR / "winget" / "kairo-phantom.yaml"
    content = manifest_path.read_text(encoding="utf-8")
    assert "MIT" in content, "winget manifest does not specify MIT license"


# ---------------------------------------------------------------------------
# config-template.toml validation
# ---------------------------------------------------------------------------
def test_config_template_exists():
    """The config template must exist."""
    config_path = INSTALLER_DIR / "config-template.toml"
    assert config_path.exists(), f"Missing config template: {config_path}"


def test_config_template_has_model_section():
    """The config template must have a [model] section."""
    config_path = INSTALLER_DIR / "config-template.toml"
    content = config_path.read_text(encoding="utf-8")
    assert "[model]" in content, "config template missing [model] section"
    assert "provider" in content, "config template missing model provider"
    assert "model_name" in content, "config template missing model_name"


# ---------------------------------------------------------------------------
# Modelfile validation
# ---------------------------------------------------------------------------
def test_modelfile_exists():
    """The Ollama Modelfile must exist."""
    modelfile_path = INSTALLER_DIR / "Modelfile"
    assert modelfile_path.exists(), f"Missing Modelfile: {modelfile_path}"


def test_modelfile_has_from_directive():
    """The Modelfile must have a FROM directive."""
    modelfile_path = INSTALLER_DIR / "Modelfile"
    content = modelfile_path.read_text(encoding="utf-8")
    assert "FROM" in content, "Modelfile missing FROM directive"


def test_modelfile_has_system_prompt():
    """The Modelfile must have a SYSTEM prompt."""
    modelfile_path = INSTALLER_DIR / "Modelfile"
    content = modelfile_path.read_text(encoding="utf-8")
    assert "SYSTEM" in content, "Modelfile missing SYSTEM prompt"


def test_modelfile_has_temperature_parameter():
    """The Modelfile must set temperature for deterministic output."""
    modelfile_path = INSTALLER_DIR / "Modelfile"
    content = modelfile_path.read_text(encoding="utf-8")
    assert "PARAMETER temperature" in content, \
        "Modelfile missing PARAMETER temperature"
