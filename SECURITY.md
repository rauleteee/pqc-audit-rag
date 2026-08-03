# Security Policy

Thanks for helping keep **pqc-audit-rag** and its users safe.

## Supported versions

This is an early-stage project; security fixes land on the latest code.

| Version | Supported |
| --- | --- |
| `main` / latest `0.1.x` | ✅ |
| older | ❌ |

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Report privately through GitHub's **[Report a vulnerability](https://github.com/rauleteee/pqc-audit-rag/security/advisories/new)**
button (repo → **Security** → **Advisories**). This opens a private advisory
visible only to the maintainer and you.

Please include, where possible:

- a description of the issue and its impact,
- steps to reproduce (a minimal example or affected input),
- affected version / commit, and
- any suggested fix or mitigation.

### What to expect

- **Acknowledgement:** within about **5 business days**.
- **Assessment & fix:** we'll work with you on a fix and coordinate a disclosure
  timeline. Please give us reasonable time to release a patch before any public
  disclosure.
- **Credit:** we're happy to credit you in the advisory/release notes unless you
  prefer to stay anonymous.

## Scope & security model

`pqc-audit-rag` is a local, static analysis + RAG tool. A few things worth knowing:

- **Static, read-only scanning.** Detection is delegated to the OSS
  [`pqc-audit`](https://pypi.org/project/pqc-audit/) engine, which parses target
  files with Python's `ast`. It **does not execute** the code it scans.
- **API keys are not persisted.** When you point the app at a hosted LLM, the key
  is used only for that request — it is masked in the UI and never written to
  disk, database or logs. Prefer per-project keys with least privilege, and rotate
  them if exposed.
- **TLS.** The "disable TLS verification" option (UI / `--insecure` /
  `PQC_RAG_LLM_VERIFY=false`) is a convenience for **trusted internal endpoints
  only**. Prefer providing your organisation's CA bundle so verification stays on.
- **Default credentials are for local development only.** The monitoring stack
  (`monitoring/docker-compose.yml`) ships throwaway defaults (`pqc:pqc` for
  Postgres, `admin:admin` for Grafana, anonymous viewing). **Change these and
  restrict network access before any non-local deployment.**
- **Guidance is informational.** Migration recommendations are generated from a
  curated corpus and an LLM; validate them against the authoritative standards
  (NIST FIPS 203/204/205, CNSA 2.0, etc.) before acting.

## Automated checks

This repository runs, on every push and pull request (see `.github/workflows/`):
CI (lint + tests + build), Bandit (static analysis), `pip-audit` and Dependabot
(dependency vulnerabilities), CodeQL, a CycloneDX SBOM, and gitleaks (secret
scanning).
