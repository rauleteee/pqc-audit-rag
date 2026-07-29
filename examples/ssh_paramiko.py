"""SSH server key generation with paramiko — all broken by Shor's algorithm.

Scenario: an SSH server or automation tool that generates host/user keys.
Migration: post-quantum hybrid key exchange for the transport; PQ signature
keys as they standardize.
"""

import paramiko

rsa_host_key = paramiko.RSAKey.generate(2048)
ecdsa_host_key = paramiko.ECDSAKey.generate()
dss_host_key = paramiko.DSSKey.generate(1024)
