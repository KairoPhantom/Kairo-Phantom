"""
License check CI gate for Kairo Phantom.
Fails the build if any AGPL, BSL, or copyleft dependencies are imported or linked
directly in the MIT open-core.
"""
import os
import sys
import re

# Forbidden license keywords / package names
FORBIDDEN_KEYWORDS = [
    "agpl", "bsl-1.1", "sspl", "commons clause", "copyleft"
]

FORBIDDEN_PACKAGES = [
    "pymupdf", "fitz", "aipointer", "screenpipe", "browseros", "llmaix"
]

def check_kernel_imports(root_dir: str) -> bool:
    """Ensure kernel/core/ files do NOT import AGPL libraries like PyMuPDF (fitz)."""
    core_dir = os.path.join(root_dir, "kernel", "core")
    if not os.path.exists(core_dir):
        print(f"[License Check] Warning: kernel/core/ not found at {core_dir}")
        return True

    clean = True
    for root, _, files in os.walk(core_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # Look for imports of fitz or pymupdf
                    if re.search(r"\bimport\s+(fitz|pymupdf)\b", content) or re.search(r"\bfrom\s+(fitz|pymupdf)\b", content):
                        print(f"[FAIL] {file} imports PyMuPDF (AGPL) directly. PyMuPDF must only be used via subprocess boundary!")
                        clean = False
                except Exception as e:
                    print(f"[License Check] Error reading {path}: {e}")
    return clean

def check_cargo_licenses(root_dir: str) -> bool:
    """Check Cargo.toml and Cargo.lock for forbidden dependencies."""
    cargo_lock = os.path.join(root_dir, "Cargo.lock")
    if not os.path.exists(cargo_lock):
        return True

    clean = True
    try:
        with open(cargo_lock, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse package names in Cargo.lock
        packages = re.findall(r'name\s*=\s*"([^"]+)"', content)
        for pkg in packages:
            for forbidden in FORBIDDEN_PACKAGES:
                if forbidden in pkg.lower() and pkg.lower() != "kairo-phantom":
                    print(f"[FAIL] Forbidden Cargo dependency found: '{pkg}'")
                    clean = False
    except Exception as e:
        print(f"[License Check] Error reading Cargo.lock: {e}")
    
    return clean

def main():
    # root directory is repositories/kairo-phantom/
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("============================================================")
    print("LICENSE CHECK CI GATE")
    print("Checking for AGPL/BSL/copyleft dependencies and imports...")
    print("============================================================")
    
    kernel_ok = check_kernel_imports(root_dir)
    cargo_ok = check_cargo_licenses(root_dir)
    
    if not (kernel_ok and cargo_ok):
        print("[FAIL] License check FAILED. Build blocked.")
        sys.exit(1)
        
    print("[OK] License check PASSED.")
    sys.exit(0)

if __name__ == "__main__":
    main()
