from pqc_audit_rag.providers import DEFAULT_PROVIDER, PROVIDERS


def test_local_is_the_default_and_keyless():
    assert DEFAULT_PROVIDER in PROVIDERS
    local = PROVIDERS[DEFAULT_PROVIDER]
    assert local.needs_key is False
    assert local.base_url.endswith("/v1")
    assert local.default_model


def test_hosted_providers_declare_a_key_and_signup():
    for slug in ("groq", "openai", "openrouter"):
        p = PROVIDERS[slug]
        assert p.needs_key is True
        assert p.base_url.startswith("https://")
        assert p.signup.startswith("https://")
        assert p.default_model


def test_custom_provider_is_blank():
    custom = PROVIDERS["custom"]
    assert custom.base_url == ""
    assert custom.default_model == ""
    assert custom.needs_key is False
