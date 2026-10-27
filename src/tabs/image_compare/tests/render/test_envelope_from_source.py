"""The comparison envelope is SOURCE space, carried in the plan.

Owner report (2026-10-27): replacing ONE image of an existing pair makes the
whole composition jump for a frame or two before it settles. Measured live on
the supervisor's instance (Xvfb + vulkan, pair 2000x1000 + 1000x1400, slot 1
replaced): transient canvas ``[1024,1024]`` with loupe radius ``48.40``, settled
``[1600,1400]`` with ``51.74``; and one frame with the magnifier object present,
``visible=True``, zero circles.

Why: every preview is normalised per side to a 1024 long edge, so the envelope
``max(w1,w2) x max(h1,h2)`` of a PREVIEW pair has a different aspect than the
envelope of the SOURCE pair (2000x1400 = 1.43 vs 1024x1024 = 1.0). While a
preview tier is on screen the canvas basis (``plan.canvas_w/h``), the drawn
content rect, the split position and every canvas-px overlay (the loupe glass
included) were fitted to that preview aspect, then re-fitted when the unified
store landed.

This file pins the design that removes the guesswork:

* ``build_canvas_plan`` sizes the live basis from the plan's SOURCE roles —
  each side's own decoded pixels (``presentation/source_tier.py``) — and records
  the resulting ``(w1,h1,w2,h2)`` as ``plan.envelope_dims``.
* every downstream owner that had been re-deriving the envelope from whatever
  tier is installed (``update_common_letterbox_geometry``,
  ``refresh_live_content_rect``) consumes that field instead.
* fallback is today's behaviour, byte-identical: no live default plan
  (export/snapshot), an active crop box (display dims are the truth there), or
  a side whose source is not decoded yet all leave ``envelope_dims is None``.

The frames are reproduced offscreen through the real apply chain
(``build_canvas_plan`` → ``apply_canvas_render_plan`` on a real ``CanvasWidget``
→ ``upload_pil_images`` → ``update_common_letterbox_geometry`` → the magnifier
plan overlay) and the assertion reads the drawn widget-px glass radius
(``runtime_state._feature_overlay_gpu._radius``) plus the drawn content rect —
not canvas-px intermediates.
"""

from __future__ import annotations

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image
from PySide6.QtGui import QColor, QImage

from core.state_management.dispatcher import Dispatcher
from core.store import Store
from core.store_viewport import SessionData
from tabs.image_compare.canvas.features.magnifier.state.store import (
    add_magnifier_model,
    set_default_magnifier_size,
    set_magnifier_enabled_flag,
)
from tabs.image_compare.canvas.presentation.plan_applicator import (
    apply_canvas_render_plan,
)
from tabs.image_compare.canvas.presentation.plan_builder import build_canvas_plan
from tabs.image_compare.state.document import DocumentModel, ImageItem
from tabs.image_compare.state.models import (
    ImageSessionState,
    PipelineCacheState,
    RenderCacheState,
)

WIDGET = (1200, 900)

# The real pair: landscape + portrait, so the source envelope is NOT square.
SOURCE_LEFT = (2000, 1000)
SOURCE_RIGHT = (1000, 1400)
SOURCE_ENVELOPE = (2000, 1400)
# Post-replace transient: each side's own PREVIEW, 1024 long edge, aspect kept.
PREVIEW_LEFT = (1024, 512)
PREVIEW_RIGHT = (731, 1024)
# Settled: unify resamples both sides onto the pair envelope.
UNIFIED = SOURCE_ENVELOPE

SIZE_RELATIVE = 0.2


@pytest.fixture(autouse=True)
def _register_image_compare_canvas_features():
    from tabs.image_compare.tab import ImageCompareTab

    ImageCompareTab().register_canvas_features()


def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _pil(size, color):
    return Image.new("RGBA", size, color)


def _qimage(size, color):
    """A preview-tier display image — ``is_preview_tier`` is QImage-only."""
    q = QImage(int(size[0]), int(size[1]), QImage.Format.Format_RGBA8888)
    q.fill(QColor(*color))
    return q


def _source_tier_key(path):
    """Cache key for a side's own pixel tier, as ``pipeline/cache`` mints it."""
    from tabs.image_compare.pipeline.cache import _pixel_key

    return _pixel_key(path, None, None)


def _store(
    display1,
    display2,
    *,
    source1=None,
    source2=None,
    crop_service=None,
    paths=("/gallery/wide_landscape.png", "/gallery/tall_portrait.png"),
):
    """A real Store: document paths, the source tier in ``pipeline.pixel``,
    the display pair (preview/unified) in ``image_state``."""
    import tabs.image_compare.bootstrap_reducers  # noqa: F401

    store = Store()
    store.create_workspace_session(session_type="image_compare", activate=True)
    p1, p2 = paths
    store.set_session_state_slot(
        "document",
        DocumentModel(
            image_list1=[ImageItem(path=p1, display_name="a")],
            image_list2=[ImageItem(path=p2, display_name="b")],
            current_index1=0,
            current_index2=0,
        ),
    )
    store.viewport.session_data = SessionData(
        image_state=ImageSessionState(), render_cache=RenderCacheState()
    )
    store.state_changed = type(
        "Sig", (), {"emit": staticmethod(lambda *_a, **_k: None)}
    )()
    store.set_dispatcher(Dispatcher(store))
    pipe = PipelineCacheState()
    if crop_service is not None:
        # Same seam texture_parts.crop_clip.crop_service_for_widget reads.
        pipe.crop_service = crop_service
    store.set_session_state_slot("pipeline", pipe)
    store.viewport.session_data.image_state.image1 = display1
    store.viewport.session_data.image_state.image2 = display2
    # The side's OWN decoded pixels: exactly what source_tier.original_pixel_tier
    # resolves. Absent -> the SOURCE role falls back to the display tier.
    if source1 is not None:
        pipe.pixel[_source_tier_key(p1)] = source1
    if source2 is not None:
        pipe.pixel[_source_tier_key(p2)] = source2
    view_state = store.viewport.view_state
    set_magnifier_enabled_flag(view_state, True)
    set_default_magnifier_size(view_state, SIZE_RELATIVE)
    add_magnifier_model(view_state, store.viewport.render_config)
    return store


def _canvas(store):
    from tabs.image_compare.canvas.widget import CanvasWidget

    _app()
    canvas = CanvasWidget()
    canvas.resize(*WIDGET)
    return canvas


def _frame(store, display1, display2):
    """One real frame: plan → apply (upload + letterbox + overlays)."""
    plan = build_canvas_plan(store, display1, display2, preserve_zoom=True)
    canvas = _canvas(store)
    apply_canvas_render_plan(canvas, plan, store=store)
    state = canvas.runtime_state
    return {
        "plan": plan,
        "content_rect": tuple(state._content_rect_px or ()),
        "letterbox": [tuple(p) if p is not None else None for p in state._letterbox_params],
        "glass_radius_px": float(state._feature_overlay_gpu._radius),
        "split": float(getattr(plan.render_scene, "split_position_visual", 0.0)),
    }


def _preview_pair_store():
    return _store(
        _qimage(PREVIEW_LEFT, (200, 40, 40, 255)),
        _qimage(PREVIEW_RIGHT, (40, 200, 40, 255)),
        source1=_pil(SOURCE_LEFT, (200, 40, 40, 255)),
        source2=_pil(SOURCE_RIGHT, (40, 200, 40, 255)),
    )


# -- (a) the plan carries SOURCE dims while the display pair is preview-tier --


def test_plan_envelope_is_source_space_while_display_is_preview_tier():
    store = _preview_pair_store()
    preview = _frame(
        store, _qimage(PREVIEW_LEFT, (200, 40, 40, 255)), _qimage(PREVIEW_RIGHT, (40, 200, 40, 255))
    )

    assert preview["plan"].envelope_dims == (*SOURCE_LEFT, *SOURCE_RIGHT), (
        "the plan must carry the SOURCE envelope (w1,h1,w2,h2), not the"
        f" installed tier's: got {preview['plan'].envelope_dims!r}"
    )
    # The canvas basis is that envelope — the aspect the settled pair will have.
    assert (preview["plan"].canvas_w, preview["plan"].canvas_h) == SOURCE_ENVELOPE


def test_source_missing_falls_back_to_the_display_tier():
    """One side not decoded yet: the plan must stay on today's display dims."""
    store = _store(
        _qimage(PREVIEW_LEFT, (200, 40, 40, 255)),
        _qimage(PREVIEW_RIGHT, (40, 200, 40, 255)),
        source1=_pil(SOURCE_LEFT, (200, 40, 40, 255)),
        source2=None,
    )
    plan = build_canvas_plan(
        store,
        _qimage(PREVIEW_LEFT, (200, 40, 40, 255)),
        _qimage(PREVIEW_RIGHT, (40, 200, 40, 255)),
        preserve_zoom=True,
    )
    assert plan.envelope_dims == (
        SOURCE_LEFT[0],
        SOURCE_LEFT[1],
        PREVIEW_RIGHT[0],
        PREVIEW_RIGHT[1],
    ), "a missing source keeps that side's display dims (no invented size)"
    # Envelope of the mixed pair: max over the known dims of each side.
    assert (plan.canvas_w, plan.canvas_h) == (
        max(SOURCE_LEFT[0], PREVIEW_RIGHT[0]),
        max(SOURCE_LEFT[1], PREVIEW_RIGHT[1]),
    )


# -- (b) the drawn loupe glass is a function of the letterboxed content only --


def test_drawn_loupe_radius_is_identical_on_preview_and_unified_frames():
    store = _preview_pair_store()
    preview = _frame(
        store, _qimage(PREVIEW_LEFT, (200, 40, 40, 255)), _qimage(PREVIEW_RIGHT, (40, 200, 40, 255))
    )
    settled = _frame(
        store, _qimage(UNIFIED, (200, 40, 40, 255)), _qimage(UNIFIED, (40, 200, 40, 255))
    )

    assert preview["content_rect"] == settled["content_rect"], (
        "the drawn content rect must not follow the installed tier: preview"
        f" {preview['content_rect']} vs settled {settled['content_rect']}"
    )
    assert preview["glass_radius_px"] == pytest.approx(
        settled["glass_radius_px"], rel=1e-6, abs=1e-6
    ), (
        "the loupe glass must be identical on the preview frame and the"
        f" unified one: {preview['glass_radius_px']:.3f}px vs"
        f" {settled['glass_radius_px']:.3f}px"
    )
    assert preview["split"] == pytest.approx(settled["split"], abs=1e-9)
    # size_relative over the canonical basis: the glass is
    # ``size_relative/2 * sqrt(canvas_w*canvas_h)`` canvas-px, converted by the
    # letterbox scale ``min(dw/canvas_w, dh/canvas_h)`` (= 0.6 here).
    assert settled["glass_radius_px"] == pytest.approx(
        0.5 * SIZE_RELATIVE * math.sqrt(SOURCE_ENVELOPE[0] * SOURCE_ENVELOPE[1]) * 0.6,
        rel=1e-6,
    )


# -- (c) the cases that must stay byte-identical to HEAD ---------------------


def test_same_size_pair_is_unchanged():
    """Equal dims: source envelope == display envelope, so nothing moves."""
    store = _store(
        _pil((800, 600), (200, 40, 40, 255)),
        _pil((800, 600), (40, 200, 40, 255)),
        source1=_pil((800, 600), (200, 40, 40, 255)),
        source2=_pil((800, 600), (40, 200, 40, 255)),
    )
    frame = _frame(
        store, _pil((800, 600), (200, 40, 40, 255)), _pil((800, 600), (40, 200, 40, 255))
    )
    # HEAD numbers for this pair: canvas == display dims, envelope 800x600 fitted
    # into the 1200x900 widget → 1200x900 (same 4:3 aspect), so the glass is
    # size_relative/2 * sqrt(800*600) * 1.5 canvas→widget.
    assert (frame["plan"].canvas_w, frame["plan"].canvas_h) == (800, 600)
    assert frame["content_rect"] == (0, 0, 1200, 900)
    assert frame["glass_radius_px"] == pytest.approx(
        0.5 * SIZE_RELATIVE * math.sqrt(800 * 600) * 1.5, rel=1e-6
    )
    # ... and the source-carrying plan matches a plan whose rounds resolve to the
    # display tier (what HEAD effectively sized from), member by member.
    head_store = _store(
        _pil((800, 600), (200, 40, 40, 255)),
        _pil((800, 600), (40, 200, 40, 255)),
    )
    head = _frame(
        head_store, _pil((800, 600), (200, 40, 40, 255)), _pil((800, 600), (40, 200, 40, 255))
    )
    assert head["plan"].envelope_dims == frame["plan"].envelope_dims
    assert head["content_rect"] == frame["content_rect"]
    assert head["letterbox"] == frame["letterbox"]
    assert head["glass_radius_px"] == frame["glass_radius_px"]
    assert (head["plan"].canvas_w, head["plan"].canvas_h) == (
        frame["plan"].canvas_w,
        frame["plan"].canvas_h,
    )


def _bordered_png(path):
    """120x80 content at (40,40) inside a 200x160 frame (autocrop fixture)."""
    canvas = Image.new("RGBA", (200, 160), (0, 0, 0, 255))
    canvas.paste(Image.new("RGBA", (120, 80), (200, 180, 160, 255)), (40, 40))
    canvas.save(str(path))
    return str(path)


def test_crop_plan_keeps_the_display_truth(tmp_path):
    """A crop box is active: display (box-clipped) dims stay the basis."""
    from shared.image_processing.autocrop import CropService

    p1 = _bordered_png(tmp_path / "a.png")
    p2 = _bordered_png(tmp_path / "b.png")
    svc = CropService()
    assert svc.get(p1) is not None and svc.get(p2) is not None
    disp1 = Image.open(p1).convert("RGBA")
    disp2 = Image.open(p2).convert("RGBA")
    store = _store(disp1, disp2, crop_service=svc, paths=(p1, p2))

    plan = build_canvas_plan(store, disp1, disp2, preserve_zoom=True)

    assert plan.envelope_dims is None, (
        "with a crop box active the box-clipped display dims are the truth;"
        " the plan must not advertise a source-space envelope"
    )
    assert (plan.canvas_w, plan.canvas_h) == (120, 80)
    assert tuple(store.runtime_cache.overlay_clip_rect) == (0, 0, 120, 80)
    # The drawn letterbox keeps fitting the display pair (HEAD-identical):
    # 120x80 fitted into 1200x900 → 1200x800, centred vertically.
    frame = _frame(store, disp1, disp2)
    assert frame["content_rect"] == (0, 50, 1200, 800)


def test_export_shaped_plan_has_no_envelope():
    """Export/snapshot plans pass target_size — today's path, no envelope."""
    store = _preview_pair_store()
    display1 = _qimage(PREVIEW_LEFT, (200, 40, 40, 255))
    display2 = _qimage(PREVIEW_RIGHT, (40, 200, 40, 255))
    plan = build_canvas_plan(
        store, display1, display2, target_size=(500, 400), preserve_zoom=True
    )
    assert plan.envelope_dims is None
    assert (plan.canvas_w, plan.canvas_h) == (500, 400)
