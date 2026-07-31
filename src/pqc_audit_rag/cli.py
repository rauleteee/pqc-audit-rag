"""Thin CLI over the pipeline: ``pqc-audit-rag audit|ingest``."""

from __future__ import annotations

import argparse
import sys

from pqc_audit_rag import monitoring
from pqc_audit_rag.config import settings
from pqc_audit_rag.pipeline import run_audit
from pqc_audit_rag.report import to_html, to_markdown
from pqc_audit_rag.synthesis import FakeSynthesizer, LLMSynthesizer


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pqc-audit-rag",
        description="Scan a project and generate a post-quantum migration plan.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("audit", help="Audit a path and print a migration report.")
    audit.add_argument("path", help="File or directory to scan.")
    fmt = audit.add_mutually_exclusive_group()
    fmt.add_argument("--md", action="store_true", help="Markdown output (default).")
    fmt.add_argument("--html", action="store_true", help="Self-contained HTML output.")
    audit.add_argument(
        "--offline",
        action="store_true",
        help="Use the deterministic synthesizer instead of the LLM.",
    )
    audit.add_argument("--model", default=None, help="LLM model (default from env).")
    audit.add_argument(
        "--index",
        default=None,
        help="Path to a persistent LanceDB index (default: build in-memory).",
    )
    audit.add_argument(
        "--rebuild", action="store_true", help="Rebuild the persistent index."
    )

    sub.add_parser("ingest", help="Build the persistent vector index from the corpus.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "ingest":
        from pqc_audit_rag.knowledge_base import ingest

        ingest.main()
        return 0

    synthesizer = FakeSynthesizer() if args.offline else LLMSynthesizer(model=args.model)
    try:
        report = run_audit(
            args.path,
            synthesizer=synthesizer,
            index_path=args.index,
            rebuild_index=args.rebuild,
        )
    except Exception as exc:  # pragma: no cover - CLI convenience
        if not args.offline:
            print(
                f"error: LLM synthesis failed ({exc}). Is the LLM endpoint up "
                f"(base_url={settings.llm_base_url})? Retry with --offline for a "
                "deterministic report.",
                file=sys.stderr,
            )
            return 1
        raise

    # Best-effort: persist the run for monitoring (no-op without PQC_RAG_PG_DSN).
    monitoring.record_run(report)

    print(to_html(report) if args.html else to_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
