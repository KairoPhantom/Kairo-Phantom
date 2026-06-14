"""
CI gate script to prevent developers or auto-fixers from introducing skipped or ignored tests.
Scans Python test files for @pytest.mark.skip/xfail and Rust files for #[ignore].
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("kairo.no_skip")

# Allowed directories to scan
TEST_PATHS = [
    "repositories/kairo-phantom/kairo-sidecar/tests",
    "repositories/kairo-phantom/phantom-core/tests"
]


def scan_python_files(path: str) -> bool:
    """Scan Python test files for skipped decorators or code-level skips."""
    clean = True
    forbidden = ["@pytest.mark.skip", "pytest.skip(", "@unittest.skip", "@pytest.mark.xfail", "pytest.xfail("]
    
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py") and file.startswith("test_"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            # Skip comment lines
                            if line.strip().startswith("#"):
                                continue
                            for keyword in forbidden:
                                if keyword in line:
                                    log.error(f"❌ Skipped Python test found in {file_path}:{line_num} -> '{line.strip()}'")
                                    clean = False
                except Exception as e:
                    log.warning(f"Could not read Python file {file_path}: {e}")
    return clean


def scan_rust_files(path: str) -> bool:
    """Scan Rust test files for #[ignore] attributes."""
    clean = True
    forbidden = ["#[ignore]"]
    
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".rs"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            # Skip comment lines
                            if line.strip().startswith("//"):
                                continue
                            for keyword in forbidden:
                                if keyword in line:
                                    log.error(f"❌ Ignored Rust test found in {file_path}:{line_num} -> '{line.strip()}'")
                                    clean = False
                except Exception as e:
                    log.warning(f"Could not read Rust file {file_path}: {e}")
    return clean


def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    clean = True
    
    # Locate test paths relative to workspace root
    for rel_path in TEST_PATHS:
        full_path = os.path.join(root_dir, os.path.relpath(rel_path, "repositories/kairo-phantom"))
        if not os.path.exists(full_path):
            # Try direct relative path lookup
            full_path = os.path.join(root_dir, rel_path)
            
        if os.path.exists(full_path):
            log.info(f"[No-Skip Gate] Scanning path: {full_path}")
            if "kairo-sidecar" in full_path:
                if not scan_python_files(full_path):
                    clean = False
            else:
                if not scan_rust_files(full_path):
                    clean = False
        else:
            log.warning(f"Test path not found, skipping scan for: {rel_path}")
            
    if not clean:
        log.error("❌ CI build failed: Skipped/ignored tests are strictly forbidden.")
        sys.exit(1)
        
    log.info("✅ No-Skip enforcement gate passed successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()
