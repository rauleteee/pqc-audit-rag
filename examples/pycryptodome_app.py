"""Key generation with pycryptodome — quantum-vulnerable public keys.

Scenario: an application that mints RSA/DSA/EC keys with pycryptodome.
Migration: RSA/EC key transport -> ML-KEM; RSA/DSA/ECDSA signatures -> ML-DSA.
"""

from Crypto.PublicKey import DSA, ECC, RSA

rsa_key = RSA.generate(2048)
dsa_key = DSA.generate(2048)
ecc_key = ECC.generate(curve="P-256")
