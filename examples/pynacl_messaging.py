"""End-to-end messaging keys with PyNaCl (libsodium).

Scenario: a messaging app using Ed25519 signatures and Curve25519 key exchange.
Migration: Ed25519 signatures -> ML-DSA; Curve25519 key exchange -> hybrid ML-KEM.
"""

from nacl.public import PrivateKey
from nacl.signing import SigningKey

signing_key = SigningKey.generate()  # Ed25519 signatures
box_key = PrivateKey.generate()  # Curve25519 (X25519) key exchange
