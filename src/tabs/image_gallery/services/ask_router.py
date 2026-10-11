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

from tabs.image_gallery.services.ai_client import AiResponseError, call_sync
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
        "max_tokens": 700,
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
        "max_tokens": 700,
    }


def _extract_text(raw: dict) -> str:
    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AiResponseError(f"unexpected response shape: {exc}") from exc
    if not isinstance(content, str) or not content.strip():
        raise AiResponseError("empty ask response")
    return content.strip()


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
