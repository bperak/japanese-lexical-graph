import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# Reload gemini_helper fresh for each test to isolate monkeypatch effects

gemini_helper = importlib.import_module("gemini_helper")


class DummyResponse:
    """Simple stand-in for the object returned by GenerativeModel.generate_content."""

    def __init__(self, text: str):
        self.text = text


@pytest.fixture
def enable_api(monkeypatch):
    """Force HAS_VALID_API_KEY to True for tests that require API availability."""

    monkeypatch.setattr(gemini_helper, "HAS_VALID_API_KEY", True)


def _patch_genai(monkeypatch, response_text: str):
    """Patch gemini_helper.genai.GenerativeModel to return DummyResponse."""

    model_mock = MagicMock()
    model_mock.generate_content.return_value = DummyResponse(response_text)

    genai_mock = SimpleNamespace(GenerativeModel=MagicMock(return_value=model_mock))
    monkeypatch.setattr(gemini_helper, "genai", genai_mock)


# ---------------------------------------------------------------------------
# Expected-use test
# ---------------------------------------------------------------------------

def test_generate_explanation_success(enable_api, monkeypatch):
    """generate_explanation should parse valid JSON and echo model_used key."""

    json_payload = (
        '{"overview":"Test","cultural_context":"Ctx","usage_examples":["ex"],"nuances":"Nuance"}'
    )
    _patch_genai(monkeypatch, json_payload)

    model_name = "gemini-2.0-flash"
    result = gemini_helper.generate_explanation("花", model_name=model_name)

    assert result["overview"] == "Test"
    assert result["cultural_context"] == "Ctx"
    assert result["usage_examples"] == ["ex"]
    assert result["nuances"] == "Nuance"
    assert result["_model_used"] == model_name


# ---------------------------------------------------------------------------
# Edge case test
# ---------------------------------------------------------------------------

def test_generate_explanation_invalid_json(enable_api, monkeypatch):
    """If Gemini returns non-JSON data, function should keep fallback fields and add generation_note."""

    bad_payload = "This is *not* JSON at all."
    _patch_genai(monkeypatch, bad_payload)

    result = gemini_helper.generate_explanation("花")
    assert "generation_note" in result
    # Overview fallback should reference the term.
    assert "花" in result["overview"]


# ---------------------------------------------------------------------------
# Failure case test
# ---------------------------------------------------------------------------

def test_generate_explanation_no_api_key(monkeypatch):
    """When API key is missing, function should return an explicit error dict."""

    monkeypatch.setattr(gemini_helper, "HAS_VALID_API_KEY", False)
    result = gemini_helper.generate_explanation("花")
    assert result == {"error": "No valid Gemini API key configured"} 