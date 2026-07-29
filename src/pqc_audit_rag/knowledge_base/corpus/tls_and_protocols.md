# Post-quantum migration in protocols (TLS, SSH, IPsec, PKI)

Where and how post-quantum algorithms slot into the protocols that use
quantum-vulnerable cryptography today.

**Sources:** IETF TLS hybrid key exchange draft-ietf-tls-ecdhe-mlkem
(https://datatracker.ietf.org/doc/draft-ietf-tls-ecdhe-mlkem/); RFC 9370
(https://www.rfc-editor.org/rfc/rfc9370); OpenSSH release notes
(https://www.openssh.com/releasenotes.html); OpenSSL release notes
(https://www.openssl.org).

## TLS 1.3 hybrid key exchange

The hybrid group **X25519MLKEM768** (formerly X25519Kyber768) combines classical
X25519 with ML-KEM-768 for the TLS key exchange, protecting session keys against
harvest-now-decrypt-later. It is deployed by major browsers and CDNs (Chrome,
Cloudflare, AWS) and supported in OpenSSL 3.5+ and BoringSSL. TLS *authentication*
(certificate signatures) migrates separately, to ML-DSA.

## SSH post-quantum key exchange

OpenSSH ships hybrid post-quantum key exchange: `sntrup761x25519-sha512` (default
since OpenSSH 9.0) and `mlkem768x25519-sha256` (added around OpenSSH 9.9/10).
These protect the confidentiality of SSH sessions now; host and user *signature*
keys (Ed25519, RSA, ECDSA) remain classical until PQ SSH signatures standardize.

## IPsec / IKEv2

RFC 9370 ("Multiple Key Exchanges in IKEv2") lets IKEv2 negotiate additional key
exchanges beyond the first, so an ML-KEM exchange can be added alongside a
classical one for a hybrid, quantum-resistant IPsec tunnel.

## X.509 / PKI and code signing

Certificates and code-signing keys using RSA or ECDSA signatures are broken by
Shor. Migrate certificate authority hierarchies to ML-DSA, and consider SLH-DSA
for long-lived root keys (hash-based assumptions). Composite and hybrid
certificate formats are being standardized in the IETF LAMPS working group.

## S/MIME and secure email

S/MIME signing and encryption built on RSA/ECDSA/ECDH migrate to ML-DSA
signatures and ML-KEM key transport as the corresponding CMS/algorithm
identifiers are standardized.
