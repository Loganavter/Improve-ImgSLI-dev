"""Backend router for the gallery "Ask AI" surface (A2).

One frozen seam: ``answer(question, context, *, backend, ...) -> AskResult``.
The question kind selects the backend (the router enforces the contract):

- **text LLM** — summaries/narration over the measured table (no images);
- **VLM** — genuinely visual questions (images in the payload, ≤1024px);
- **Jev stub** — routing/priority is declared as an interface and raises
  ``AskNotConfigured`` (the UI degrades visibly, "routing not enabled").

Transport is the existing ``ai_client.call_sync`` (no new HTTP client). All
sync calls must run on a GenericWorker — never the UI thread. Advisory only:
the result is text/priority, never a mutation of rank/selection/store.
Fail-open: any backend error yields an ``AskResult`` with an error note, never
fabricated text.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from tabs.image_gallery.services.ai_client import (
    DEFAULT_FALLBACK_MODELS,
    AiResponseError,
    _ai_debug,
    call_sync,
)
from tabs.image_gallery.services.vlm import _encode_image

#: Backends the router can dispatch to.
BACKEND_TEXT = "text"
BACKEND_VLM = "vlm"
BACKEND_JEV = "jev"

#: Deferred routing gate (Jev): no text generation, no vision — routing only.
JEV_STUB = BACKEND_JEV

_VISUAL_HINTS = (
    "look",
    "visually",
    "visual",
    " see",
    "show me",
    "describe",
    "color",
    "colour",
    "blur",
    "grain",
    "sharpen",
    "artifact",
    "halo",
    "banding",
    "noise",
    "detail",
    "texture",
    "fring",
    "wrong",
)

_ROUTING_HINTS = (
    "route",
    "prioritize",
    "prioritise",
    "priority",
    " rank",
    "which series",
    "which one first",
    "order of",
    "triage order",
)

#: Vision payload budget: never upload the whole folder.
VLM_MAX_IMAGES = 6

_NAMING_RULE = (
    " Images are identified ONLY by the given labels (img_1, img_2, …). Use "
    "those labels verbatim; never infer, translate or guess a filename — the "
    "label carries no meaning about the image."
)

_TEXT_PROMPT = (
    "You answer questions about a gallery of image-processing variants "
    "(upscalers, restorations) of the SAME picture. You are given the locally "
    "measured metrics (quality 0-100, higher is always better) and artifact "
    "severities; treat them as authoritative and do not contradict them. "
    "Answer in 1-4 plain sentences. Do not restate the raw metric table; give "
    "the practical read a human should act on. Never invent measurements."
    + _NAMING_RULE
)

_VISION_PROMPT = (
    "You answer questions about images in a gallery of processing variants of "
    "the SAME picture. You are given the locally measured metrics as "
    "authoritative context and, for visual questions, the images themselves. "
    "Judge only what you can actually SEE; if you cannot see it, say so. "
    "Answer in 1-4 plain sentences. Label any visual claim as an unverified AI "
    "read, never a verdict."
    + _NAMING_RULE
)


class AskNotConfigured(Exception):
    """Raised by the Jev routing stub — the backend is not wired yet."""


@dataclass(frozen=True)
class AskResult:
    """One answer (or a visible degrade). Never mutates gallery state."""

    text: str
    backend: str
    priority: int | None = None
    confidence: float | None = None
    cached: bool = False
    error: str | None = None


def route_backend(question: str, context: dict) -> str:
    """Pick a backend from the question kind (text / vlm / jev)."""
    q = str(question or "").strip().lower()
    if not q:
        return BACKEND_TEXT
    if any(hint in q for hint in _ROUTING_HINTS):
        return BACKEND_JEV
    if any(hint in q for hint in _VISUAL_HINTS):
        return BACKEND_VLM
    return BACKEND_TEXT


def _context_block(context: dict) -> str:
    """Compact measured-context block handed to the model."""
    try:
        ctx = context or {}
        lines = [
            f"Scope: {ctx.get('label', '')} ({ctx.get('kind', '')}), "
            f"{int(ctx.get('count', 0) or 0)} item(s), mode={ctx.get('mode', '')}"
        ]
        src = ctx.get("source")
        if src:
            lines.append(f"Source: {src}")
        for it in list(ctx.get("items", []) or []):
            metrics = it.get("metrics") or {}
            sev = it.get("severities") or {}
            met_txt = ", ".join(f"{k}={v}%" for k, v in metrics.items())
            sev_txt = ", ".join(f"{k}:{v}" for k, v in sev.items())
            line = f"- {it.get('alias') or it.get('name', '')}"
            badge = it.get("badge")
            if badge:
                line += f" [{badge}]"
            if met_txt:
                line += f" {met_txt}"
            if sev_txt:
                line += f" | {sev_txt}"
            lines.append(line)
        return "\n".join(lines)
    except Exception:
        return ""


def build_text_payload(question: str, context: dict, *, model: str) -> dict:
    """Text-only chat payload — NO image bytes (asserted by tests)."""
    text = (
        f"{_TEXT_PROMPT}\n\nQUESTION: {str(question or '').strip()}\n\n"
        f"MEASURED CONTEXT (authoritative):\n{_context_block(context)}"
    )
    return {
        "model": model,
        "messages": [{"role": "user", "content": [{"type": "text", "text": text}]}],
        "max_tokens": 4096,
    }


def build_vision_payload(question: str, context: dict, *, model: str) -> dict:
    """Vision chat payload: text + up to ``VLM_MAX_IMAGES`` downscaled images."""
    content: list[dict] = [
        {
            "type": "text",
            "text": (
                f"{_VISION_PROMPT}\n\nQUESTION: {str(question or '').strip()}\n\n"
                f"MEASURED CONTEXT (authoritative):\n{_context_block(context)}"
            ),
        }
    ]
    for it in list((context or {}).get("items", []) or [])[:VLM_MAX_IMAGES]:
        try:
            path = Path(str(it.get("path")))
            mime, data = _encode_image(path)
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{data}"}}
            )
        except Exception:
            continue
    return {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 4096,
    }


def _coerce_text(value) -> str:
    """Best-effort text out of a chat message field (str or parts list)."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for part in value:
            try:
                if isinstance(part, dict):
                    if part.get("type") in (None, "text", "output_text"):
                        parts.append(str(part.get("text", "")))
                    elif part.get("text"):
                        parts.append(str(part["text"]))
                elif isinstance(part, str):
                    parts.append(part)
            except Exception:
                continue
        return "".join(parts).strip()
    return ""


def _extract_text(raw: dict) -> str:
    """Pull the answer text out of a chat completion ``message.content``."""
    try:
        message = raw["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AiResponseError(f"unexpected response shape: {exc}") from exc
    if not isinstance(message, dict):
        raise AiResponseError("unexpected message shape")
    text = _coerce_text(message.get("content"))
    if text:
        return text
    finish = None
    try:
        finish = raw["choices"][0].get("finish_reason")
    except Exception:
        pass
    _ai_debug(
        "ask empty content finish_reason=%s usage=%s",
        finish,
        raw.get("usage") if isinstance(raw, dict) else None,
    )
    raise AiResponseError(f"empty ask response (finish_reason={finish})")


def _is_openrouter(base_url: str) -> bool:
    return "openrouter" in str(base_url or "").lower()


def _apply_openrouter_extensions(payload: dict, base_url: str, model: str) -> dict:
    """OpenRouter knobs so a reasoning model always returns answer text.

    ``z-ai/glm-5.3-flash`` (and family) reasons *mandatorily* with default
    effort ``max`` — roughly 95% of ``max_tokens`` goes to hidden reasoning,
    so a small budget returns ``finish_reason: length`` with empty ``content``
    (observed: HTTP 200, zero chars). Cap the effort at ``low`` and raise
    ``max_tokens`` so the visible answer always has room; route to a healthy
    provider and fall back if the primary is exhausted.
    """
    if not _is_openrouter(base_url):
        return payload
    payload["reasoning"] = {"effort": "low"}
    payload["provider"] = {
        "require_parameters": True,
        "sort": "throughput",
        "allow_fallbacks": True,
    }
    chain = [model] + [m for m in DEFAULT_FALLBACK_MODELS if m and m != model]
    if len(chain) > 1:
        payload["models"] = chain
        payload["route"] = "fallback"
    return payload


def _jev_stub() -> AskResult:
    """Deferred routing backend: interface declared, not wired."""
    raise AskNotConfigured("routing backend is not enabled")


def answer(
    question: str,
    context: dict,
    *,
    backend: str,
    base_url: str = "",
    api_key: str = "",
    model: str = "",
    transport: Callable[[str, str, dict], dict] | None = None,
) -> AskResult:
    """Answer *question* over *context* via *backend*. Worker thread only.

    ``transport`` defaults to :func:`ai_client.call_sync`; tests inject a fake
    to capture the payload and avoid the network. Any failure (not configured,
    backend error, malformed response) returns an ``AskResult`` whose ``error``
    is set and whose ``text`` is empty — never a fabricated answer.
    """
    backend = str(backend or BACKEND_TEXT).strip().lower() or BACKEND_TEXT
    if backend == "auto":
        backend = route_backend(question, context)

    if backend == BACKEND_JEV:
        try:
            return _jev_stub()
        except AskNotConfigured as exc:
            return AskResult(text="", backend=BACKEND_JEV, error=str(exc))

    if not (base_url and api_key and model):
        return AskResult(
            text="",
            backend=backend,
            error="AI is not configured (set the API key/model in Settings).",
        )

    call = transport or call_sync
    try:
        if backend == BACKEND_VLM:
            payload = build_vision_payload(question, context, model=model)
        else:
            backend = BACKEND_TEXT
            payload = build_text_payload(question, context, model=model)
        payload = _apply_openrouter_extensions(payload, base_url, model)
        raw = call(base_url, api_key, payload)
        return AskResult(text=_extract_text(raw), backend=backend)
    except Exception as exc:
        return AskResult(
            text="",
            backend=backend,
            error=str(exc) or exc.__class__.__name__,
        )


__all__ = [
    "BACKEND_JEV",
    "BACKEND_TEXT",
    "BACKEND_VLM",
    "AskNotConfigured",
    "AskResult",
    "answer",
    "build_text_payload",
    "build_vision_payload",
    "route_backend",
]
