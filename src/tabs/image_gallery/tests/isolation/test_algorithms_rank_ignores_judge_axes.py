"""INVARIANT: the Algorithms order is built from LOCAL measurements only.

The Algorithms backend ranks what the deterministic detectors measured: the
engine records / ``item.metrics``. A VLM scorecard (``item.analysis``) was
produced by the OTHER backend, so it must not move an Algorithms rank — not
even through an axis the model named in free form.

Falsification story (red on ``int/backend-isolation``): the fusion call passes
the ACTIVE metric profile, which may carry the judge's own axis entries
(``MetricProfile.axis_entries``), and ``rank_fusion._judge_scores`` reads those
numbers out of ``item.analysis``. Two items with byte-identical ``metrics``
therefore stop tying as soon as one of them carries a scorecard: the paid
axis changes its quality and its rank. Measured here as an OBSERVABLE rank/
value difference, never as "``_judge_scores`` exists".
"""

from __future__ import annotations

from pathlib import Path

from tabs.image_gallery.models import AiAnalysisResult, AiAxisProposal, GalleryItem
from tabs.image_gallery.services.metric_profile import MetricProfile
from tabs.image_gallery.services.rank_fusion import (
    item_quality,
    measured_axes_for,
    rank_series,
)

#: A profile the model shaped for this series: the registry half the local
#: detectors answer PLUS one axis the judge named (no local producer exists for
#: it). The Algorithms backend's fusion call passes the active profile, so this
#: is the shape in which a judge-named axis reaches ``rank_series``.
_JUDGE_AXIS = "halation"


def _algorithms_profile() -> MetricProfile:
    return MetricProfile(
        axis_ids=("sharpness", "noise"),
        mode="batch_synthetic",
        source="series",
        axis_entries=(
            AiAxisProposal(
                name=_JUDGE_AXIS,
                definition="glow around bright edges",
                scale="0-100",
                score=-1,
            ),
        ),
    )


def _item(name: str) -> GalleryItem:
    """Two items with IDENTICAL local measurements (a real near-tie)."""
    item = GalleryItem(path=Path(f"/gallery/{name}"), mtime_ns=1)
    item.metrics.update({"sharpness": 200.0, "noise": 0.2})
    return item


def _scorecard(*, axis: str, score: int) -> AiAnalysisResult:
    return AiAnalysisResult(
        description="",
        tags=(),
        model="judge-model",
        analyzed_at_iso="t",
        axes={axis: score},
        axis_proposals=(AiAxisProposal(name=axis, score=score),),
    )


def test_algorithms_rank_ignores_judge_axes() -> None:
    profile = _algorithms_profile()

    # Non-vacuous: the judge-named axis really is in the profile's axis set, so
    # a difference below is caused by the scorecard, not by the axis being
    # absent from the question.
    assert _JUDGE_AXIS in measured_axes_for(None, profile=profile)

    a = _item("a.png")
    b = _item("b.png")
    baseline_ranks = rank_series([a, b], profile=profile)
    baseline_quality = [item_quality(item, profile=profile) for item in (a, b)]

    # The same two items, same metrics; b now carries the AI backend's answer.
    b.analysis = _scorecard(axis=_JUDGE_AXIS, score=100)

    leaked_ranks = rank_series([a, b], profile=profile)
    leaked_quality = [item_quality(item, profile=profile) for item in (a, b)]

    assert baseline_quality == [65.0, 65.0], (
        "fixture sanity: identical metrics must produce identical local quality"
    )
    assert leaked_quality == baseline_quality, (
        "the Algorithms backend's quality must not read item.analysis: "
        f"baseline={baseline_quality!r} with-analysis={leaked_quality!r}"
    )
    assert leaked_ranks == baseline_ranks, (
        "a VLM scorecard changed the Algorithms order: "
        f"baseline={baseline_ranks!r} with-analysis={leaked_ranks!r}"
    )
