# Standards bodies and the evolving PQC landscape

Who is standardizing post-quantum cryptography and what is still in flight.

**Sources:** NIST Post-Quantum Cryptography project incl. the HQC selection
(2025) and signature on-ramp (https://csrc.nist.gov/projects/post-quantum-cryptography);
IETF (https://datatracker.ietf.org), RFC 9370 (https://www.rfc-editor.org/rfc/rfc9370);
ETSI Quantum-Safe Cryptography (https://www.etsi.org).

## NIST — core standards and the on-ramp

NIST finalized ML-KEM (FIPS 203), ML-DSA (FIPS 204) and SLH-DSA (FIPS 205) in
2024. It also selected **HQC** in 2025 as a backup key-encapsulation mechanism
based on different (code-based) hardness assumptions than lattice-based ML-KEM,
and is running an "on-ramp" to standardize additional post-quantum signature
schemes for algorithm diversity.

## IETF — protocol integration

The IETF integrates post-quantum algorithms into protocols: the TLS working group
(hybrid key-exchange groups), LAMPS (PKIX/CMS composite and hybrid certificates)
and IPSECME (RFC 9370 multiple key exchanges in IKEv2). Protocol migration is
mostly hybrid classical + PQC during the transition.

## ETSI and ISO/IEC

ETSI's Quantum-Safe Cryptography group and ISO/IEC working groups publish
guidance and are standardizing post-quantum mechanisms and migration frameworks
complementary to NIST.

## Migration prioritization framework

A common framework prioritizes migration by (1) the confidentiality lifetime of
the data and (2) system exposure. Because of harvest-now-decrypt-later, key
establishment (ML-KEM) is generally migrated before signatures (ML-DSA), and
long-lived-secret systems before short-lived ones.
