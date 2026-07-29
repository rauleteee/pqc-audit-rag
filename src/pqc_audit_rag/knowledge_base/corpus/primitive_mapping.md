# Primitive-to-PQC migration mapping

How to map each detected quantum-vulnerable primitive to a NIST post-quantum
target, by usage context.

**Sources:** NIST FIPS 203/204/205 (https://csrc.nist.gov/projects/post-quantum-cryptography);
NSA Commercial National Security Algorithm Suite 2.0 (https://www.nsa.gov).

## Key exchange / key establishment -> ML-KEM (FIPS 203)

Vulnerable primitives used for establishing shared keys are broken by Shor's
algorithm and must migrate to ML-KEM:

- RSA key transport / RSA-OAEP key wrapping -> ML-KEM-768 (hybrid during transition).
- Finite-field Diffie-Hellman (DH) -> ML-KEM-768.
- Elliptic-Curve Diffie-Hellman (ECDH, e.g. P-256, X25519) -> ML-KEM-768.

Transition guidance: deploy a **hybrid KEM** (e.g. X25519 + ML-KEM-768) so
security holds if either component is later found weak.

## Digital signatures -> ML-DSA (FIPS 204), or SLH-DSA (FIPS 205)

Vulnerable signature primitives are broken by Shor and must migrate:

- RSA signatures (PKCS#1 v1.5, PSS) -> ML-DSA-65.
- DSA -> ML-DSA-65.
- ECDSA (P-256, secp256k1, ...) -> ML-DSA-65.
- EdDSA (Ed25519, Ed448) -> ML-DSA-65.

Use **SLH-DSA** instead where hash-based assumptions are preferred (long-lived
root/firmware keys). Both are quantum-safe signature standards.

## Symmetric encryption -> larger keys (not broken)

- AES-128 -> AES-256 (Grover halves the effective key strength; AES-256 restores it).
- AES-192 / AES-256 -> acceptable, no action strictly required.

## Hashing -> larger / modern digests

- MD5, SHA-1 -> SHA-256 / SHA-384 / SHA3 (already broken for collisions; replace now).
- SHA-256 -> acceptable; use SHA-384/512 for long-term or high-assurance contexts.

## Already post-quantum (no action)

- ML-KEM (Kyber), ML-DSA (Dilithium), SLH-DSA (SPHINCS+) usage is already
  post-quantum and should be reported as informative, not as a defect.
