"""Already post-quantum — should be reported as INFO, not a vulnerability.

Scenario: code that has already migrated to NIST post-quantum algorithms via
liboqs. The scanner recognizes these as post-quantum (informative), so the
verdict is clean.
"""

import oqs

kem = oqs.KeyEncapsulation("ML-KEM-768")  # Kyber key encapsulation
sig = oqs.Signature("ML-DSA-65")  # Dilithium signatures
