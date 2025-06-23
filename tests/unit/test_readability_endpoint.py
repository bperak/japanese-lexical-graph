import pytest
import json
import app


def test_no_text_provided(client=None):
    # Use Flask test_client directly
    client = app.app.test_client()
    resp = client.post('/readability', json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['error'] == 'No text provided'


def test_short_text_returns_400(monkeypatch):
    client = app.app.test_client()
    # Use text shorter than default threshold
    short_text = "あ" * 100
    resp = client.post('/readability', json={'text': short_text})
    assert resp.status_code == 400
    data = resp.get_json()
    assert 'Need at least' in data['error']


def test_successful_readability(monkeypatch):
    client = app.app.test_client()
    # Stub assess_readability in app module
    stub_result = {'score': 2.2, 'level': 'Lower-advanced', 'chars_processed': 500}
    monkeypatch.setattr(app, 'assess_readability', lambda text: stub_result)
    resp = client.post('/readability', json={'text': 'dummy payload'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == stub_result 