"""Streamlit UI for the PQC Audit RAG assistant.

A clean, single-page interface — styled after the pqc-scanner HTML report
(verdict banner + severity chips + per-exposure cards) — to run an audit on a
real local project and read the retrieved, cited migration guidance. Collects
thumbs up/down feedback (seed of the monitoring phase).

Run:  streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

from pqc_audit_rag import monitoring
from pqc_audit_rag.config import settings
from pqc_audit_rag.feedback import record_feedback
from pqc_audit_rag.models import AuditReport
from pqc_audit_rag.pipeline import run_audit
from pqc_audit_rag.providers import DEFAULT_PROVIDER, PROVIDERS
from pqc_audit_rag.synthesis import FakeSynthesizer, LLMSynthesizer

TONE = {
    "CRITICAL": "#d12d2d",
    "MEDIUM": "#c77800",
    "INFO": "#1f7ab5",
    "clean": "#2e7d32",
}

EXAMPLES_DIR = Path(__file__).parents[1] / "examples"

# One-line description per bundled example (for the picker).
EXAMPLE_DESCRIPTIONS = {
    "vulnerable_sample.py": "Kitchen sink · pyca/cryptography — RSA, ECC, DSA, DH, Ed25519, AES",
    "ssh_paramiko.py": "SSH host keys · paramiko — RSA, ECDSA, DSA (all CRITICAL)",
    "pycryptodome_app.py": "Key generation · pycryptodome — RSA, DSA, EC (all CRITICAL)",
    "pynacl_messaging.py": "Messaging keys · PyNaCl — Ed25519 + Curve25519 (CRITICAL)",
    "weak_hashing.py": "Weakened, not broken · MD5, SHA-1, AES-128 (all MEDIUM)",
    "post_quantum_ready.py": "Already post-quantum · ML-KEM + ML-DSA (INFO — clean verdict)",
}

_CSS = """
<style>
  .pqc-sub { color: #888; font-size: .85rem; margin: -.4rem 0 1rem; }
  .pqc-sub code { background: rgba(128,128,128,.15); padding: .1rem .35rem; border-radius: 4px; }
  .pqc-verdict { border-left: 5px solid var(--tone); background: rgba(128,128,128,.10);
     padding: .9rem 1.15rem; border-radius: 8px; margin: .3rem 0 1.1rem; }
  .pqc-verdict .label { font-size: .68rem; text-transform: uppercase; letter-spacing: .08em; color: #888; }
  .pqc-verdict .text { font-size: 1.12rem; font-weight: 600; color: var(--tone); margin-top: .15rem; }
  .pqc-chips { display: flex; flex-wrap: wrap; gap: .5rem; margin-bottom: 1.4rem; }
  .pqc-chip { display: inline-flex; align-items: baseline; gap: .4rem; padding: .3rem .7rem;
     border-radius: 999px; background: rgba(128,128,128,.14); font-size: .85rem; }
  .pqc-chip b { font-size: 1.05rem; }
  .pqc-chip.critical b { color: #d12d2d; } .pqc-chip.medium b { color: #c77800; }
  .pqc-chip.info b { color: #1f7ab5; }
  .pqc-card { border: 1px solid rgba(128,128,128,.28); border-left: 5px solid var(--tone);
     border-radius: 8px; padding: .85rem 1.1rem; margin-bottom: .9rem; }
  .pqc-card h3 { margin: 0 0 .3rem; font-size: 1.02rem; }
  .pqc-badge { font-weight: 700; font-size: .72rem; padding: .12rem .5rem; border-radius: 999px;
     border: 1px solid var(--tone); color: var(--tone); margin-right: .5rem; vertical-align: middle; }
  .pqc-target { color: #888; font-size: .9rem; }
  .pqc-cites { color: #888; font-size: .8rem; margin-top: .5rem; }
</style>
"""


def _tone(counts: dict) -> str:
    for sev in ("CRITICAL", "MEDIUM", "INFO"):
        if counts.get(sev):
            return sev
    return "clean"


def _render_report(report: AuditReport) -> None:
    e = html.escape
    counts = report.counts
    tone_color = TONE[_tone(counts)]

    st.markdown(
        f'<p class="pqc-sub">scanned <code>{e(report.path)}</code> · synthesized by '
        f"<code>{e(report.generated_by)}</code></p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="pqc-verdict" style="--tone:{tone_color}">'
        f'<div class="label">Verdict</div>'
        f'<div class="text">{e(report.verdict)}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="pqc-chips">'
        f'<span class="pqc-chip critical"><b>{counts.get("CRITICAL", 0)}</b> CRITICAL</span>'
        f'<span class="pqc-chip medium"><b>{counts.get("MEDIUM", 0)}</b> MEDIUM</span>'
        f'<span class="pqc-chip info"><b>{counts.get("INFO", 0)}</b> INFO</span>'
        f'<span class="pqc-chip"><b>{counts.get("total", 0)}</b> total</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    if not report.recommendations:
        st.success("No quantum-vulnerable cryptography detected in scope.")
        return

    for rec in report.recommendations:
        tone_color = TONE.get(rec.severity, TONE["clean"])
        steps = "".join(f"<li>{e(s)}</li>" for s in rec.steps)
        cites = (
            f'<div class="pqc-cites">Sources: {e("; ".join(rec.citations))}</div>'
            if rec.citations
            else ""
        )
        st.markdown(
            f'<div class="pqc-card" style="--tone:{tone_color}">'
            f'<h3><span class="pqc-badge" style="--tone:{tone_color}">{e(rec.severity)}</span>'
            f"{e(rec.algorithm)} — {e(rec.usage.replace('_', ' '))} "
            f'<span class="pqc-target">→ {e(rec.migration_target)}</span></h3>'
            f"<p>{e(rec.summary)}</p><ul>{steps}</ul>{cites}</div>",
            unsafe_allow_html=True,
        )


def _feedback(report: AuditReport) -> None:
    st.divider()
    st.caption("Was this migration report useful?")
    run_id = st.session_state.get("run_id")
    col_up, col_down, _ = st.columns([1, 1, 6])
    if col_up.button("👍 Helpful", use_container_width=True):
        record_feedback(report, "up", run_id=run_id)
        st.toast("Thanks for the feedback!")
    if col_down.button("👎 Not useful", use_container_width=True):
        record_feedback(report, "down", run_id=run_id)
        st.toast("Thanks — we'll use this to improve.")


def main() -> None:
    st.set_page_config(page_title="PQC Audit RAG", page_icon="🔐", layout="centered")
    st.markdown(_CSS, unsafe_allow_html=True)

    st.title("🔐 PQC Audit RAG")
    st.caption(
        "Scan a Python project for quantum-vulnerable cryptography and get a "
        "cited post-quantum migration plan."
    )

    with st.sidebar:
        st.header("Audit")

        example_files = sorted(p.name for p in EXAMPLES_DIR.glob("*.py"))
        options = example_files + ["Custom path…"]
        default_index = (
            example_files.index("vulnerable_sample.py")
            if "vulnerable_sample.py" in example_files
            else 0
        )
        choice = st.selectbox("Example project", options, index=default_index)
        if choice == "Custom path…":
            path = st.text_input("Project path", value="examples/vulnerable_sample.py")
        else:
            path = str(EXAMPLES_DIR / choice)
            if choice in EXAMPLE_DESCRIPTIONS:
                st.caption(EXAMPLE_DESCRIPTIONS[choice])
        mode = st.radio(
            "Synthesis",
            ["LLM", "Offline (deterministic)"],
            help="LLM calls a model (local Ollama or a hosted API); "
            "Offline is deterministic and needs nothing.",
        )
        provider_key = st.selectbox(
            "LLM provider",
            list(PROVIDERS),
            index=list(PROVIDERS).index(DEFAULT_PROVIDER),
            format_func=lambda k: PROVIDERS[k].label,
            help="Local Ollama (free, slow) or a remote OpenAI-compatible API.",
        )
        provider = PROVIDERS[provider_key]
        base_url = st.text_input("Base URL", value=provider.base_url)
        model = st.text_input(
            "LLM model", value=provider.default_model or settings.llm_model
        )
        api_key = st.text_input(
            "API key" if provider.needs_key else "API key (optional)",
            value="",
            type="password",
            help="Used only for this request, never stored. Leave blank for "
            "local Ollama or a keyless endpoint.",
        )
        st.caption(
            "🔒 Masked and kept only in this browser session — never written to "
            "disk, database or logs."
        )
        if provider.needs_key and provider.signup:
            st.caption(f"Get a free key → {provider.signup}")
        if provider.note:
            st.caption(provider.note)

        verify_tls: bool | str = True
        with st.expander("Advanced — TLS (internal / self-signed endpoints)"):
            ca_bundle = st.text_input(
                "CA bundle path (recommended for a private CA)", value=""
            )
            insecure = st.checkbox(
                "Disable TLS certificate verification (insecure)",
                value=False,
                help="Only for a trusted internal endpoint whose CA this machine "
                "does not know. Prefer the CA bundle path above.",
            )
            if ca_bundle.strip():
                verify_tls = ca_bundle.strip()
            elif insecure:
                verify_tls = False
        method = st.selectbox(
            "Retrieval method",
            ["rerank", "hybrid", "dense", "text"],
            help="Evaluated in evaluation/RESULTS.md; 'rerank' scored best.",
        )
        top_k = st.slider("Retrieved passages (top-k)", 1, 8, settings.top_k)
        max_tokens = st.slider(
            "Max output tokens",
            200,
            1200,
            settings.llm_max_tokens,
            step=50,
            help="Higher = fuller steps, slower. Too low truncates the guidance.",
        )
        run = st.button("Run audit", type="primary", use_container_width=True)

    if run:
        target = Path(path.strip())
        if not target.exists():
            st.error(f"Path not found: {target}")
            return
        offline = mode.startswith("Offline")
        synthesizer = (
            FakeSynthesizer()
            if offline
            else LLMSynthesizer(
                model=model,
                base_url=base_url or None,
                api_key=api_key or None,
                verify_tls=verify_tls,
                max_tokens=max_tokens,
            )
        )
        try:
            with st.status("Running audit…", expanded=True) as status:
                bar = st.progress(0.0)

                def _on_event(message: str, progress) -> None:
                    status.write(message)
                    if progress is not None:
                        bar.progress(min(max(progress, 0.0), 1.0))

                report = run_audit(
                    str(target),
                    synthesizer=synthesizer,
                    method=method,
                    top_k=top_k,
                    on_event=_on_event,
                )
                status.update(label="Audit complete", state="complete", expanded=False)
        except Exception as exc:  # pragma: no cover - UI convenience
            endpoint = getattr(synthesizer, "base_url", settings.llm_base_url)
            used_model = getattr(synthesizer, "model", "")
            st.error(
                f"LLM synthesis failed: {exc}\n\n"
                f"Endpoint actually used: `{endpoint}`  ·  model: `{used_model}`\n\n"
                "Check that the **Base URL** is OpenAI-compatible (usually ends in "
                "`/v1`), the **model** name matches one the endpoint serves, and "
                "that the host is reachable from this machine (VPN / firewall?). "
                "Or switch to Offline mode."
            )
            return
        st.session_state["report"] = report
        # Best-effort: persist for monitoring (no-op without PQC_RAG_PG_DSN).
        st.session_state["run_id"] = monitoring.record_run(report)

    report = st.session_state.get("report")
    if report is not None:
        _render_report(report)
        _feedback(report)
    else:
        st.info("Enter a project path in the sidebar and click **Run audit**.")


main()
