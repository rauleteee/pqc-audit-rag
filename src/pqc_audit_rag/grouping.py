"""Group raw scanner findings into exposures.

The scanner emits one ``Finding`` per call site. For migration guidance we care
about *distinct* exposures, so we group by ``(library, algorithm, usage)`` — the
same key the OSS CBOM layer uses — and carry the occurrence count and locations.
"""

from __future__ import annotations

from collections import OrderedDict

from pqc_scanner.findings import Finding

from pqc_audit_rag.models import Exposure

_SEVERITY_ORDER = {"CRITICAL": 0, "MEDIUM": 1, "INFO": 2}


def group_exposures(findings: list[Finding]) -> list[Exposure]:
    """Collapse findings into exposures, worst severity first."""
    groups: OrderedDict[tuple[str, str, str], list[Finding]] = OrderedDict()
    for f in findings:
        key = (f.library, f.algorithm, f.usage.value)
        groups.setdefault(key, []).append(f)

    exposures: list[Exposure] = []
    for (library, algorithm, usage), group in groups.items():
        rep = group[0]
        exposures.append(
            Exposure(
                library=library,
                algorithm=algorithm,
                usage=usage,
                classification=rep.classification.value,
                severity=rep.severity.value,
                migration_target=rep.migration_target,
                occurrences=len(group),
                locations=[f"{f.path}:{f.line}" for f in group],
                representative_symbol=rep.symbol,
            )
        )

    exposures.sort(key=lambda e: _SEVERITY_ORDER.get(e.severity, 3))
    return exposures
