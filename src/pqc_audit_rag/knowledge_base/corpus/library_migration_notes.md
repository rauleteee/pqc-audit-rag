# Per-library migration notes (Python)

How common Python cryptographic libraries generate quantum-vulnerable keys and
what each should migrate to. None ship production ML-KEM/ML-DSA yet, so during
transition they are typically bridged via liboqs / the OpenSSL oqs-provider.

**Sources:** Open Quantum Safe project (https://openquantumsafe.org); the
respective library documentation (pyca/cryptography, PyNaCl, paramiko, PyJWT,
pyOpenSSL, pycryptodome); NIST FIPS 203/204/205.

## Python `cryptography` (pyca)

`rsa.generate_private_key(...)`, `ec.generate_private_key(curve)` and
`dh.generate_parameters(...)` produce RSA, elliptic-curve and finite-field
Diffie-Hellman keys — all broken by Shor's algorithm. Migrate signatures to
ML-DSA and key establishment to ML-KEM. pyca/cryptography does not yet expose
post-quantum primitives; bridge via liboqs-python or an OpenSSL 3.x build with
the oqs-provider until native support lands.

## PyNaCl / libsodium

`SigningKey` uses Ed25519 for signatures and `Box`/`SealedBox` use Curve25519
(X25519) for key exchange. Both rest on the elliptic-curve discrete log problem
and are broken by Shor. Migrate Ed25519 signatures to ML-DSA and the Curve25519
key exchange to a hybrid X25519 + ML-KEM scheme.

## paramiko (SSH)

`RSAKey`, `ECDSAKey` and `Ed25519Key` generate SSH keys that are quantum-broken.
For the SSH *transport*, adopt a post-quantum hybrid key exchange (OpenSSH
`sntrup761x25519-sha512` or `mlkem768x25519-sha256`) so session confidentiality
is protected now; post-quantum SSH *signature* keys are still maturing.

## PyJWT / authlib / python-jose (JOSE / JWT)

`RS256`, `ES256` and `EdDSA` sign tokens with RSA, ECDSA and EdDSA respectively —
all Shor-vulnerable. JOSE/COSE registration of post-quantum algorithms is in
progress; until ML-DSA algorithm identifiers are standardized, reduce token
lifetimes and plan the swap behind an algorithm-agile signing layer.

## pyOpenSSL / OpenSSL (X.509 / TLS)

`crypto.PKey().generate_key(TYPE_RSA|TYPE_EC, ...)` creates RSA/EC certificate
and TLS keys. Migrate certificate signatures to ML-DSA (or SLH-DSA for long-lived
roots), using OpenSSL 3.x with the oqs-provider; composite/hybrid certificates
are under IETF LAMPS standardization.

## pycryptodome

`RSA.generate(bits)`, `DSA.generate(bits)` and `ECC.generate(curve=...)` produce
quantum-vulnerable keys. Map RSA/DSA/ECDSA signatures to ML-DSA and RSA/EC key
transport to ML-KEM; pycryptodome has no post-quantum primitives, so bridge via
liboqs during migration.
