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


# ---------------------------------------------------------------------------
# 2. the provenance marker is empty until someone was asked to analyze
# ---------------------------------------------------------------------------


def _item(name: str, *, analysis: bool = False, metrics: bool = True):
    from tabs.image_gallery.models import (
        AiAnalysisResult,
        AnalysisStatus,
        GalleryItem,
    )

    item = GalleryItem(path=Path(f"/gallery/{name}"), mtime_ns=1)
    if metrics:
        item.metrics.update({"sharpness": 40.0})
    if analysis:
        item.analysis = AiAnalysisResult(
            description="",
            tags=(),
            model="model/A",
            analyzed_at_iso="t",
            axes={"sharpness": 70},
        )
    return item, AnalysisStatus


def test_a_passively_measured_card_claims_nothing() -> None:
    """The defect: the warm folder-open pass fills metrics → every card said ALG."""
    from tabs.image_gallery.ui.card.provenance import marker_text

    item, _ = _item("passive.png")
    assert marker_text(item) == "", (
        "nothing was REQUESTED for this card — a filled metrics dict is not a "
        "claim about who analyzed it (owner 2026-10-27)"
    )
    assert marker_text(item, domain="algorithms") == ""


def test_an_explicit_local_run_earns_the_local_token() -> None:
    from tabs.image_gallery.ui.card.provenance import marker_text

    item, _ = _item("asked.png")
    assert marker_text(item, domain="algorithms", requested=True) == "ALG", (
        "the user asked for the Algorithms numbers — the card may say so"
    )


def test_a_request_without_a_finished_pass_claims_nothing() -> None:
    from tabs.image_gallery.ui.card.provenance import marker_text

    item, _ = _item("empty.png", metrics=False)
    assert marker_text(item, domain="algorithms", requested=True) == "", (
        "the request is not the result: no local analysis landed yet"
    )


def test_a_scorecard_claims_the_ai_token_in_any_domain() -> None:
    from tabs.image_gallery.ui.card.provenance import marker_text

    item, _ = _item("ai.png", analysis=True)
    assert marker_text(item) == "AI"
    assert marker_text(item, domain="algorithms") == "AI", (
        "an AiAnalysisResult IS the answer to 'who analyzed this card'"
    )


def test_a_queued_ai_card_claims_the_ai_token_only_in_the_ai_domain() -> None:
    from tabs.image_gallery.ui.card.provenance import marker_text

    item, AnalysisStatus = _item("queued.png", metrics=False)
    item.analysis_status = AnalysisStatus.PENDING
    assert marker_text(item, domain="ai") == "AI", (
        "the card is queued for the AI domain — it WILL be analyzed by the AI"
    )
    assert marker_text(item, domain="algorithms") == "", (
        "the Algorithms view shows no AI numbers and no local run was asked for"
    )


def test_the_translated_token_is_used() -> None:
    from tabs.image_gallery.ui.card.provenance import marker_text

    item, _ = _item("ai.png", analysis=True)

    def ru(key, default):
        return {"image_gallery.card.source_ai": "ИИ"}.get(key, default)

    assert marker_text(item, translate=ru) == "ИИ"


def test_requested_for_reads_the_controller_field() -> None:
    """The painters' seam: the flag IS ``_analysis_requested_gen == _folder_gen``."""
    from tabs.image_gallery.ui.card.provenance import requested_for

    owner = SimpleNamespace(_analysis_requested_gen=-1, _folder_gen=7)
    widget = SimpleNamespace(_owner_for_triage=lambda: owner)
    grid = SimpleNamespace(_gallery_widget=widget)
    card = SimpleNamespace(parent=lambda: grid)

    assert requested_for(card) is False, "a passive pass is not a request"
    owner._analysis_requested_gen = 6
    assert requested_for(card) is False, "a request for the PREVIOUS folder"
    owner._analysis_requested_gen = 7
    assert requested_for(card) is True
    # A card without any gallery ancestry claims nothing (never raises).
    assert requested_for(SimpleNamespace(parent=lambda: None)) is False


def test_an_explicit_analyze_stamps_the_folder_generation(monkeypatch) -> None:
    from tabs.image_gallery.controller import GalleryController
    from tabs.image_gallery.use_cases import ai_analysis

    monkeypatch.setattr(ai_analysis, "analyze", lambda owner, ctx: "ran")
    monkeypatch.setattr(ai_analysis, "reanalyze", lambda owner, ctx: "ran")
    ctx = SimpleNamespace(backend="algorithms", targets=())

    owner = SimpleNamespace(
        _folder_gen=3,
        _analysis_requested_gen=-1,
        _judge_run=None,
    )
    assert GalleryController.analyze(owner, ctx) == "ran"
    assert owner._analysis_requested_gen == 3, (
        "Analyze is the explicit request for THIS folder generation"
    )

    owner._analysis_requested_gen = -1
    GalleryController.reanalyze(owner, ctx)
    assert owner._analysis_requested_gen == 3


def test_a_new_folder_generation_drops_the_request(monkeypatch) -> None:
    from tabs.image_gallery.controller import GalleryController

    owner = SimpleNamespace(_folder_gen=3, _analysis_requested_gen=3)
    GalleryController._next_folder_gen(owner)
    assert owner._folder_gen == 4
    assert owner._analysis_requested_gen == -1, (
        "the fresh folder was not requested: its cards claim nothing"
    )
