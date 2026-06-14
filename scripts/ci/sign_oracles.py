#!/usr/bin/env python3
"""
scripts/ci/sign_oracles.py - Ed25519 signing utility for oracles.py.
"""
import os
import sys
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(script_dir))
    sidecar_dir = os.path.join(repo_root, "kairo-sidecar", "sidecar")
    oracles_path = os.path.join(sidecar_dir, "oracles.py")
    pub_path = os.path.join(sidecar_dir, "oracles.py.pub")
    sig_path = os.path.join(sidecar_dir, "oracles.py.sig")
    key_path = os.path.join(sidecar_dir, "oracles.py.key")

    if not os.path.exists(oracles_path):
        print(f"Error: oracles.py not found at {oracles_path}")
        sys.exit(1)

    # Load or generate private key
    if os.path.exists(key_path):
        print("Loading existing Ed25519 private key...")
        with open(key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
    else:
        print("Generating new Ed25519 private key...")
        private_key = ed25519.Ed25519PrivateKey.generate()
        pem_private = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        with open(key_path, "wb") as f:
            f.write(pem_private)

    # Save public key in PEM format
    public_key = private_key.public_key()
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(pub_path, "wb") as f:
        f.write(pem_public)

    # Sign oracles.py
    with open(oracles_path, "rb") as f:
        data = f.read()

    signature = private_key.sign(data)
    with open(sig_path, "wb") as f:
        f.write(signature)

    print(f"Success! Signed {oracles_path}")
    print(f"  Public key written to: {pub_path}")
    print(f"  Signature written to:  {sig_path}")

if __name__ == "__main__":
    main()
