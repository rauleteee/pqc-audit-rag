# Algorithm details: why each is broken and where it is used

Background on the quantum-vulnerable primitives, to ground migration decisions.

**Sources:** NIST FIPS 186-5 Digital Signature Standard
(https://csrc.nist.gov/pubs/fips/186-5/final); NIST FIPS 203/204/205; NIST
Post-Quantum Cryptography project (https://csrc.nist.gov/projects/post-quantum-cryptography).

## RSA — broken by Shor

RSA security rests on the hardness of integer factorization. Shor's algorithm
factors large integers in polynomial time on a quantum computer, so RSA-2048,
RSA-3072 and RSA-4096 are all broken. RSA is used for key transport / encryption
and for signatures: migrate key transport to ML-KEM and signatures to ML-DSA.

## Elliptic curves (ECDSA / ECDH) and named curves

Elliptic-curve cryptography relies on the elliptic-curve discrete logarithm
problem, also broken by Shor. Common curves: NIST P-256/P-384/P-521, Curve25519
(X25519 for ECDH, Ed25519 for signatures), and secp256k1 (used in Bitcoin and
Ethereum). ECDH key exchange migrates to ML-KEM; ECDSA/EdDSA signatures migrate
to ML-DSA.

## DSA and finite-field Diffie-Hellman

DSA signatures and finite-field Diffie-Hellman (DH) key agreement over MODP
groups (1024/2048/3072-bit) are broken by Shor. DSA is additionally deprecated:
FIPS 186-5 no longer approves DSA for generating signatures. DH migrates to
ML-KEM; DSA migrates to ML-DSA.

## EdDSA (Ed25519 / Ed448)

EdDSA is an Edwards-curve signature scheme, fast and widely used in SSH, JOSE and
messaging protocols. Like ECDSA it is broken by Shor and migrates to ML-DSA.

## Symmetric keys, hashes and Grover

Grover's algorithm gives only a quadratic speedup against symmetric primitives,
so sizes are increased rather than replaced: AES-128 drops to roughly 64-bit
post-quantum strength, so prefer AES-256. For hashing, SHA-256 remains
acceptable, with SHA-384/SHA-512 or SHA-3 preferred for long-term or
high-assurance use; MD5 and SHA-1 are already broken and must be replaced.
