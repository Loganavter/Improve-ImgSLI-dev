"""A2 — ``ask_router`` routing, payload shape, and fail-open answers.

No network: the transport is injected (or ``call_sync`` monkeypatched). The
router enforces the backend contract — text questions carry NO image bytes,
visual questions do, routing questions degrade visibly (Jev stub).
"""

from __future__ import annotations

import pytest

from tabs.image_gallery.services import ask_router
from tabs.image_gallery.services.ask_router import (
    BACKEND_JEV,
    BACKEND_TEXT,
    BACKEND_VLM,
    AskResult,
    answer,
    build_text_payload,
    build_vision_payload,
    route_backend,
)

_CTX = {
    "kind": "selection",
    "label": "Selection",
    "count": 1,
    "mode": "fidelity",
    "source": None,
    "items": [
        {
            "name": "a.png",
            "alias": "img_1",
            "path": "/g/a.png",
            "metrics": {"sharpness": 50},
            "severities": {"banding": "mild"},
            "badge": "★",
        }
    ],
    "names": {"img_1": "a.png"},
}


def test_empty_question_routes_to_text():
    assert route_backend("", _CTX) == BACKEND_TEXT
    assert route_backend("Summary", _CTX) == BACKEND_TEXT


def test_visual_question_routes_to_vlm():
    assert route_backend("what is visually wrong here?", _CTX) == BACKEND_VLM
    assert route_backend("describe the color", _CTX) == BACKEND_VLM


def test_routing_question_routes_to_jev():
    assert route_backend("prioritize this series", _CTX) == BACKEND_JEV
    assert route_backend("which series should I route first?", _CTX) == BACKEND_JEV


def test_text_payload_has_no_image_bytes():
    payload = build_text_payload("Summary", _CTX, model="m")
    content = payload["messages"][0]["content"]
    assert all(part["type"] == "text" for part in content)
    assert "image_url" not in repr(payload)


def test_text_payload_uses_opaque_alias_not_filename():
    payload = build_text_payload("Summary", _CTX, model="m")
    text = payload["messages"][0]["content"][0]["text"]
    assert "img_1" in text
    assert "a.png" not in text
    assert "label" in text.lower()


def test_vision_payload_embeds_downscaled_image(monkeypatch):
    monkeypatch.setattr(ask_router, "_encode_image", lambda p: ("png", "QUJD"))
    payload = build_vision_payload("what is wrong?", _CTX, model="m")
    content = payload["messages"][0]["content"]
    assert content[0]["type"] == "text"
    assert any(
        part["type"] == "image_url" and "data:image/png;base64,QUJD" in part["image_url"]["url"]
        for part in content
    )


def test_answer_text_uses_transport_and_returns_text():
    captured = {}

    def fake_transport(base_url, api_key, payload):
        captured["payload"] = payload
        return {"choices": [{"message": {"content": "Looks clean."}}]}

    result = answer(
        "Summary",
        _CTX,
        backend=BACKEND_TEXT,
        base_url="http://x",
        api_key="k",
        model="m",
        transport=fake_transport,
    )
    assert isinstance(result, AskResult)
    assert result.text == "Looks clean."
    assert result.backend == BACKEND_TEXT
    assert "image_url" not in repr(captured["payload"])


def test_answer_vlm_routes_images(monkeypatch):
    monkeypatch.setattr(ask_router, "_encode_image", lambda p: ("png", "QUJD"))
    captured = {}

    def fake_transport(base_url, api_key, payload):
        captured["payload"] = payload
        return {"choices": [{"message": {"content": "Blurry edges."}}]}

    result = answer(
        "what is wrong?",
        _CTX,
        backend=BACKEND_VLM,
        base_url="http://x",
        api_key="k",
        model="m",
        transport=fake_transport,
    )
    assert result.text == "Blurry edges."
    assert "image_url" in repr(captured["payload"])


def test_answer_jev_stub_degrades_visibly_without_fabricating():
    def boom(*a, **k):  # pragma: no cover - must never be called
        raise AssertionError("transport must not be reached for the Jev stub")

    result = answer(
        "prioritize",
        _CTX,
        backend=BACKEND_JEV,
        base_url="http://x",
        api_key="k",
        model="m",
        transport=boom,
    )
    assert result.text == ""
    assert result.error
    assert "routing" in result.error.lower()


def test_extract_text_accepts_parts_list():
    raw = {
        "choices": [
            {"message": {"content": [{"type": "text", "text": "hello "}, {"type": "text", "text": "world"}]}}
        ]
    }
    assert ask_router._extract_text(raw) == "hello world"


def test_extract_text_empty_content_is_an_error():
    raw = {"choices": [{"message": {"content": ""}, "finish_reason": "length"}]}
    with pytest.raises(ask_router.AiResponseError):
        ask_router._extract_text(raw)


def test_openrouter_caps_reasoning_effort_and_raises_budget():
    """Mandatory-reasoning models default to effort `max`; we must cap it low."""
    payload = ask_router._apply_openrouter_extensions(
        {"model": "m", "messages": []}, "https://openrouter.ai/api/v1", "m"
    )
    assert payload["reasoning"] == {"effort": "low"}
    assert payload["provider"]["sort"] == "throughput"
    assert "m" in payload["models"]


def test_openrouter_extensions_noop_for_plain_openai():
    payload = ask_router._apply_openrouter_extensions(
        {"model": "m", "messages": []}, "https://api.openai.com/v1", "m"
    )
    assert "reasoning" not in payload
    assert "provider" not in payload


def test_answer_openrouter_payload_has_room_for_the_answer():
    captured = {}

    def fake_transport(base_url, api_key, payload):
        captured["payload"] = payload
        return {"choices": [{"message": {"content": "ok"}}]}

    answer(
        "Summary",
        _CTX,
        backend=BACKEND_TEXT,
        base_url="https://openrouter.ai/api/v1",
        api_key="k",
        model="m",
        transport=fake_transport,
    )
    payload = captured["payload"]
    assert payload["max_tokens"] >= 2048
    assert payload["reasoning"] == {"effort": "low"}


def test_answer_not_configured_is_a_visible_error():
    result = answer("Summary", _CTX, backend=BACKEND_TEXT, transport=lambda *a: {})
    assert result.text == ""
    assert result.error


def test_answer_backend_exception_yields_error_result():
    def failing(base_url, api_key, payload):
        raise RuntimeError("network exploded")

    result = answer(
        "Summary",
        _CTX,
        backend=BACKEND_TEXT,
        base_url="http://x",
        api_key="k",
        model="m",
        transport=failing,
    )
    assert result.text == ""
    assert "exploded" in result.error
