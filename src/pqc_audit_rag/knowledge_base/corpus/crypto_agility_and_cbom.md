# Crypto-agility, inventory (CBOM) and hybrid transition

Practices that make a post-quantum migration feasible and safe.

**Sources:** NIST SP 1800-38, NCCoE Migration to Post-Quantum Cryptography
(https://www.nccoe.nist.gov); CycloneDX cryptographic assets (https://cyclonedx.org);
Germany BSI and France ANSSI transition guidance.

## Cryptographic inventory and CBOM

The first migration step is inventory: enumerate where cryptography is used —
algorithms, key sizes, protocols, certificates and their locations. This is a
Cryptography Bill of Materials (CBOM). CycloneDX 1.6 adds `cryptographic-asset`
components for exactly this. The guiding principle: "you can't migrate what you
can't see." NIST SP 1800-38 recommends building this inventory before migrating.

## Crypto-agility

Crypto-agility is designing systems so algorithms can be swapped without
re-architecting: abstract cryptographic operations behind interfaces, avoid
hard-coded algorithm identifiers, and support negotiation and versioning. An
agile design lets you drop in ML-KEM/ML-DSA now and change again later if a
scheme is weakened.

## Hybrid / combiner strategy

During the transition, combine a classical and a post-quantum algorithm (for
example X25519 + ML-KEM-768) so the result stays secure if either component is
later broken. Hybrid key establishment is recommended by NIST, Germany's BSI and
France's ANSSI for the transition period.

## Testing, performance and rollout

Post-quantum keys and signatures are larger and can change handshake sizes and
latency, so pilot in non-critical paths, measure performance, run interop tests,
then roll out. Prioritize systems handling long-lived secrets and those exposed
to harvest-now-decrypt-later first.
