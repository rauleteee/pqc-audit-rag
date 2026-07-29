"""Sample module with a spread of quantum-vulnerable cryptography.

Used for demos and the LLM evaluation (each call is a distinct exposure the
scanner detects). The imported libraries do not need to be installed — pqc-audit
detects usage statically via the AST.
"""

from cryptography.hazmat.primitives.asymmetric import dh, dsa, ec, ed25519, rsa
from cryptography.hazmat.primitives.ciphers import algorithms

# RSA key generation (key generation, CRITICAL).
rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# Elliptic-curve key generation (key generation, CRITICAL).
ec_key = ec.generate_private_key(ec.SECP256R1())

# DSA key generation (key generation, CRITICAL).
dsa_key = dsa.generate_private_key(key_size=2048)

# Finite-field Diffie-Hellman parameters (key exchange, CRITICAL).
dh_params = dh.generate_parameters(generator=2, key_size=2048)

# Ed25519 signing key (key generation / signing, CRITICAL).
ed_key = ed25519.Ed25519PrivateKey.generate()

# AES-128 symmetric cipher (encryption, MEDIUM under Grover).
cipher = algorithms.AES(b"0" * 16)
