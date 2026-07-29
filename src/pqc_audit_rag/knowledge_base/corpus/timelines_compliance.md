# Post-quantum migration timelines and compliance drivers

Regulatory deadlines that drive PQC migration priority. Dates are approximate
and summarized from public guidance; verify against the primary source before
client use.

## United States — NSA CNSA 2.0

The NSA Commercial National Security Algorithm Suite 2.0 sets a timeline for
National Security Systems to adopt post-quantum algorithms (ML-KEM, ML-DSA):
software/firmware signing should support and prefer CNSA 2.0 algorithms first,
with broad adoption expected across the late 2020s and a target of exclusive use
of post-quantum algorithms by 2033 for many classes of systems. Source: NSA,
"Commercial National Security Algorithm Suite 2.0".

## United States — OMB / NIST migration guidance

OMB memorandum M-23-02 directs US federal agencies to inventory cryptographic
systems and prioritize migration to post-quantum cryptography. NIST SP 1800-38
(NCCoE "Migration to Post-Quantum Cryptography") provides practical migration
playbooks and emphasizes building a cryptographic inventory (CBOM) first.

## European Union

The EU published a Coordinated Implementation Roadmap for the transition to
post-quantum cryptography, with member-state guidance:

- **Germany (BSI):** recommends starting migration now, hybrid schemes during
  transition, and prioritizing systems exposed to "harvest-now, decrypt-later".
- **France (ANSSI):** phased approach, recommending hybrid classical+PQC through
  a transition period rather than an immediate hard cutover.
- Coordinated EU targets commonly cite high-risk use cases by ~2030 and broad
  migration by ~2035.

## Harvest-now, decrypt-later (why it is urgent)

Adversaries can capture encrypted traffic today and decrypt it once a
cryptographically relevant quantum computer exists. Data with a long
confidentiality lifetime (health, legal, state secrets, long-lived credentials)
is at risk **now**, even before quantum computers arrive — which is why key
establishment migration (ML-KEM) is often prioritized over signatures.
