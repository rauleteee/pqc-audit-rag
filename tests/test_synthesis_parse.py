from pqc_audit_rag.synthesis import _extract_payload


def test_plain_json():
    s, steps = _extract_payload('{"summary": "do X", "steps": ["a", "b"]}')
    assert s == "do X"
    assert steps == ["a", "b"]


def test_json_in_markdown_fence():
    s, steps = _extract_payload('```json\n{"summary": "hi", "steps": ["one"]}\n```')
    assert s == "hi"
    assert steps == ["one"]


def test_json_embedded_in_prose():
    s, steps = _extract_payload('Sure!\n{"summary": "y", "steps": []}\nHope this helps')
    assert s == "y"
    assert steps == []


def test_steps_as_string_is_wrapped():
    s, steps = _extract_payload('{"summary": "z", "steps": "just one"}')
    assert steps == ["just one"]


def test_prose_fallback_becomes_summary():
    s, steps = _extract_payload("Migrate RSA to ML-KEM as soon as possible.")
    assert s == "Migrate RSA to ML-KEM as soon as possible."
    assert steps == []


def test_empty_stays_empty():
    assert _extract_payload("") == ("", [])
    assert _extract_payload("   ") == ("", [])


def test_truncated_json_salvages_summary_and_complete_steps():
    # max_tokens cut the reply mid-way: unterminated JSON, last step incomplete.
    truncated = (
        '{ "summary": "RSA-2048 is broken by Shor; migrate to ML-KEM.", '
        '"steps": [ "Inventory all RSA call sites.", "Swap to ML-KEM-768.", '
        '"Re-run the sca'
    )
    summary, steps = _extract_payload(truncated)
    assert summary == "RSA-2048 is broken by Shor; migrate to ML-KEM."
    # The two complete steps are kept; the truncated third is dropped.
    assert steps == ["Inventory all RSA call sites.", "Swap to ML-KEM-768."]
    # Crucially, the raw braces are never shown as the summary.
    assert not summary.startswith("{")


def test_truncated_json_with_escapes():
    truncated = (
        '{ "summary": "Use \\"hybrid\\" mode (X25519 + ML-KEM).", "steps": [ "Step'
    )
    summary, steps = _extract_payload(truncated)
    assert summary == 'Use "hybrid" mode (X25519 + ML-KEM).'
    assert steps == []
