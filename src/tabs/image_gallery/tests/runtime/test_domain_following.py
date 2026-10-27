"""The gallery follows its DURABLE judgment domain (owner report 2026-10-27).

Three reported symptoms, one cause — a surface acting on what it happened to
have instead of on what the user asked for:

- the local detection stack (torch/torchvision/piq + two deprecation warnings)
  was warmed at page build whatever the domain, so an AI-only session paid it;
- every card said "АЛГ" because the passive folder-open pass fills ``metrics``,
  and the marker read "metrics present" as "the detectors analyzed this";
- that same passive pass stamped the USER-VISIBLE analysis phase, so the card
  badge blinked "alg → ai" on folder open in the AI domain while the numbers it
  produced are not even shown there.

Falsification story per test: each one names the defect it kills and is red on
``2794da9cd`` (the warm-up had no domain argument at all; the marker called
``analysis_source`` with no notion of an explicit run; the local pass stamped
its phase unconditionally).
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tabs.image_gallery.services import warmup


@pytest.fixture(autouse=True)
def _reset_warmup():
    warmup.reset_for_tests()
    warmup.set_domain_provider(None)
    os.environ.pop("IMGSLI_GALLERY_NO_WARMUP", None)
    yield
    warmup.reset_for_tests()
    warmup.set_domain_provider(None)
    os.environ.pop("IMGSLI_GALLERY_NO_WARMUP", None)


def _spy_threads(monkeypatch) -> list:
    """Record the warm-up threads instead of starting them."""
    started: list = []

    class _Thread:
        def __init__(self, *, target, name, daemon):
            started.append((target, name, daemon))

        def start(self):
            return None

    monkeypatch.setattr(warmup.threading, "Thread", _Thread)
    return started


# ---------------------------------------------------------------------------
# 1. the warm-up follows the durable domain
# ---------------------------------------------------------------------------


def test_the_warmup_is_not_scheduled_in_the_ai_domain(monkeypatch) -> None:
    started = _spy_threads(monkeypatch)
    warmup.set_domain_provider(lambda: "ai")

    assert warmup.schedule_warmup("page created") is False, (
        "the AI domain reads no local numbers — the torch/piq import must not "
        "start there (owner 2026-10-27)"
    )
    assert started == [], "no warm-up thread may be created in the AI domain"


def test_the_ai_domain_does_not_consume_the_once_flag(monkeypatch) -> None:
    """A later switch to Algorithms must still warm: the skip is not a start."""
    started = _spy_threads(monkeypatch)
    warmup.set_domain_provider(lambda: "ai")
    assert warmup.schedule_warmup("page created") is False

    warmup.set_domain_provider(lambda: "algorithms")
    assert warmup.schedule_warmup("gallery tab activated") is True, (
        "the first Algorithms activation after an AI start must warm the stack"
    )
    assert len(started) == 1
    assert started[0][0] is warmup.warm_local_backends
    # …and still once per process.
    assert warmup.schedule_warmup("again") is False


def test_an_explicit_domain_argument_beats_the_provider(monkeypatch) -> None:
    started = _spy_threads(monkeypatch)
    warmup.set_domain_provider(lambda: "algorithms")

    assert warmup.schedule_warmup("switch", domain="ai") is False, (
        "an explicit domain is the caller's answer; the provider is only asked "
        "when the caller has none"
    )
    assert started == []
    assert warmup.schedule_warmup("switch", domain="algorithms") is True


def test_the_kill_switch_still_disables_the_warmup(monkeypatch) -> None:
    started = _spy_threads(monkeypatch)
    monkeypatch.setenv("IMGSLI_GALLERY_NO_WARMUP", "1")
    warmup.set_domain_provider(lambda: "algorithms")

    assert warmup.schedule_warmup("page created") is False
    assert started == []


def test_the_domain_switch_schedules_the_warmup_from_the_durable_domain(
    monkeypatch,
) -> None:
    """The switch is the ONE place the local stack becomes worth its cost."""
    from tabs.image_gallery.controller import GalleryController
    from tabs.image_gallery.use_cases import ai_analysis

    calls: list = []
    monkeypatch.setattr(
        ai_analysis, "activate_judgment_domain", lambda owner, domain: None
    )
    monkeypatch.setattr(
        warmup,
        "schedule_warmup",
        lambda reason="", *, domain=None: calls.append((reason, domain)),
    )

    owner = SimpleNamespace(_judgment_domain="ai", widget=SimpleNamespace())
    GalleryController.activate_judgment_domain(owner, "ai")
    assert calls and calls[-1][1] == "ai", (
        "the switch passes the DURABLE domain it just stored, not a guess"
    )

    owner._judgment_domain = "algorithms"
    GalleryController.activate_judgment_domain(owner, "algorithms")
    assert calls[-1][1] == "algorithms"
