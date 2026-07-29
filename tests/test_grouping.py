from pqc_scanner import scan

from pqc_audit_rag.grouping import group_exposures


def test_groups_rsa_keygen_as_one_critical_exposure(vulnerable_file):
    exposures = group_exposures(scan(str(vulnerable_file)))

    assert len(exposures) == 1
    exp = exposures[0]
    assert exp.severity == "CRITICAL"
    assert "RSA" in exp.algorithm
    assert exp.occurrences == 1
    assert exp.migration_target  # a suggested PQC target is present
    assert exp.locations and exp.locations[0].endswith(":2")


def test_exposures_sorted_worst_first(vulnerable_file):
    # Add an AES (MEDIUM) use alongside the RSA (CRITICAL) one.
    src = vulnerable_file.read_text() + (
        "from cryptography.hazmat.primitives.ciphers import algorithms\n"
        "cipher = algorithms.AES(b'0' * 16)\n"
    )
    vulnerable_file.write_text(src)

    exposures = group_exposures(scan(str(vulnerable_file)))
    severities = [e.severity for e in exposures]
    # CRITICAL must come before MEDIUM.
    assert severities.index("CRITICAL") < severities.index("MEDIUM")
