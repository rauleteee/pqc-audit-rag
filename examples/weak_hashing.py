"""Weakened — not broken by Shor — primitives (MEDIUM severity).

Scenario: legacy hashing and 128-bit symmetric encryption. These are not broken
by a quantum computer, only weakened by Grover; the fix is larger sizes / modern
digests, not a post-quantum replacement.
"""

import hashlib

from cryptography.hazmat.primitives.ciphers import algorithms

md5_digest = hashlib.md5(b"data")
sha1_digest = hashlib.sha1(b"data")
aes128 = algorithms.AES(b"0" * 16)
