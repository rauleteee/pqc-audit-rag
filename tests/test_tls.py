from pqc_audit_rag.config import _parse_verify
from pqc_audit_rag.synthesis import LLMSynthesizer


def test_parse_verify_toggle_and_path():
    assert _parse_verify("true") is True
    assert _parse_verify("") is True
    assert _parse_verify("false") is False
    assert _parse_verify("0") is False
    assert _parse_verify("/etc/ssl/company-ca.pem") == "/etc/ssl/company-ca.pem"


def test_synthesizer_defaults_to_verify_true():
    assert LLMSynthesizer().verify_tls is True


def test_synthesizer_accepts_explicit_verify():
    assert LLMSynthesizer(verify_tls=False).verify_tls is False
    assert LLMSynthesizer(verify_tls="/ca.pem").verify_tls == "/ca.pem"
