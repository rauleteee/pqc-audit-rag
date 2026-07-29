from pqc_audit_rag.synthesis import (
    SYNTHESIS_STYLES,
    LLMSynthesizer,
    _system_prompt,
)


def test_prompt_styles_present():
    assert {"concise", "detailed", "checklist"} <= set(SYNTHESIS_STYLES)


def test_system_prompt_includes_json_instruction():
    prompt = _system_prompt("detailed")
    assert "JSON" in prompt
    # Unknown style falls back to the concise style.
    assert _system_prompt("nonexistent") == _system_prompt("concise")


def test_synthesizer_prompt_style_defaults_from_settings():
    assert LLMSynthesizer().prompt_style  # non-empty default
    assert LLMSynthesizer(prompt_style="checklist").prompt_style == "checklist"
