# NIST post-quantum cryptography standards (FIPS 203/204/205)

On 13 August 2024, NIST published the first three finalized post-quantum
cryptography standards. These are the migration targets for quantum-vulnerable
public-key cryptography. Source: NIST, "NIST Releases First 3 Finalized
Post-Quantum Encryption Standards" (2024-08-13).

## FIPS 203 — ML-KEM (Module-Lattice Key-Encapsulation Mechanism)

ML-KEM (derived from CRYSTALS-Kyber) is the primary standard for **key
establishment / key exchange**. It replaces quantum-vulnerable key-exchange and
key-transport schemes such as RSA key transport, finite-field Diffie-Hellman
(DH) and Elliptic-Curve Diffie-Hellman (ECDH). Parameter sets: ML-KEM-512,
ML-KEM-768 (recommended default), ML-KEM-1024. Migration guidance commonly
recommends a hybrid (classical + ML-KEM) key exchange during transition.

## FIPS 204 — ML-DSA (Module-Lattice Digital Signature Algorithm)

ML-DSA (derived from CRYSTALS-Dilithium) is the primary standard for **digital
signatures**. It replaces quantum-vulnerable signature schemes such as RSA
signatures, DSA, ECDSA and EdDSA (Ed25519/Ed448). Parameter sets: ML-DSA-44,
ML-DSA-65 (recommended default), ML-DSA-87. Use ML-DSA for most signing use
cases: code signing, certificates, tokens, firmware.

## FIPS 205 — SLH-DSA (Stateless Hash-Based Digital Signature Algorithm)

SLH-DSA (derived from SPHINCS+) is a **hash-based signature** standard, a
conservative backup for signatures whose security rests only on hash functions
rather than lattice assumptions. It is slower and has larger signatures than
ML-DSA, but is a defensible choice where diversity of assumptions matters (e.g.
long-lived root keys, firmware signing). Prefer ML-DSA for general use; consider
SLH-DSA where hash-based security is required.

## Symmetric and hash primitives

Symmetric ciphers and hashes are not broken by Shor's algorithm. Grover's
algorithm gives a quadratic speedup, so doubling key/output sizes restores the
security margin: prefer **AES-256** over AES-128, and **SHA-384/SHA-512 or
SHA3** over shorter digests. SHA-1 and MD5 are already broken for collision
resistance and must be replaced regardless of quantum concerns.
