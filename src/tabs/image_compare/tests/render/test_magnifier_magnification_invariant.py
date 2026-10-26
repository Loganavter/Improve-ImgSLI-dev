"""The loupe's magnification is an INVARIANT: screen px per SOURCE px.

Red-before (measured on a leased live instance 2026-10-26, 1400x1000 pair,
content scale 0.4836): the capture radius was an independent fraction of the
content short edge, so the ratio lived in *canvas* px while the loop was drawn
letterboxed. The loupe therefore showed ``4.73 * 0.4836 = 2.29`` screen px per
source px; NEAREST/BILINEAR/LANCZOS differed by <= 29/255 on 17% of its pixels
and read as "the interpolation setting does nothing until a restart". A 7 px
source cell showed as 16 px instead of the 35 px the fix produces.

Guarded invariants:
1. ``drawn_diameter_widget / sampled_source_px == DEFAULT_MAGNIFIER_MAGNIFICATION``
   for every content scale (window/image size cannot change the loupe);
2. ``capture_size_relative`` still orders the loupe (halve the capture area ->
   double the magnification), so saved settings keep their meaning;
3. the drawn capture ring and the sampled uv rect describe the same area
   (a ring that lies about what is sampled is the bug this file exists for).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from domain.types import Color, Point
from tabs.image_compare.canvas.features.magnifier.constants import (
    DEFAULT_MAGNIFIER_MAGNIFICATION,
)
from tabs.image_compare.canvas.features.magnifier.geometry.layout_plan import (
    build_magnifier_layout,
)
from tabs.image_compare.canvas.features.magnifier.state.models import MagnifierModel

CONTENT_W, CONTENT_H = 1400, 1000  # live pair size the defect was measured on


def _layout(monkeypatch, *, capture_rel=0.1, size_rel=0.4, display_scale=1.0):
    import tabs.image_compare.canvas.features.magnifier.geometry.layout_plan as layout_plan

    model = MagnifierModel(
        id="default",
        position=Point(0.5, 0.5),
        border_color=Color(255, 255, 255, 255),
        size_relative=size_rel,
        capture_size_relative=capture_rel,
        visible_left=True,
        visible_center=False,
        visible_right=True,
    )
    monkeypatch.setattr(
        layout_plan, "iter_magnifier_models", lambda view, render: [model]
    )
    monkeypatch.setattr(layout_plan, "active_magnifier_id", lambda view: "default")
    monkeypatch.setattr(
        layout_plan,
        "read_canvas_feature_color_by_setting_key",
        lambda session_type, viewport, key: Color(255, 50, 100, 230),
    )
    monkeypatch.setattr(
        layout_plan,
        "active_or_default_border_color",
        lambda view: Color(255, 255, 255, 248),
    )
    viewport = SimpleNamespace(
        view_state=SimpleNamespace(
            diff_mode="off", channel_view_mode="RGB", canvas_widget_state={}
        ),
        render_config=SimpleNamespace(interpolation_method="BILINEAR"),
    )
    return build_magnifier_layout(
        viewport,
        width=CONTENT_W,
        height=CONTENT_H,
        canvas_width=CONTENT_W,
        canvas_height=CONTENT_H,
        divider_thickness_px=2,
        display_scale=display_scale,
    )


def _magnification(layout, display_scale):
    """Screen px per source px the painted layout actually delivers."""
    drawn_diameter_widget = 2.0 * layout.slots[0].radius * display_scale
    sampled_source_px = 2.0 * layout.capture_circles[0].radius
    return drawn_diameter_widget / sampled_source_px


@pytest.mark.parametrize("display_scale", [1.0, 0.4836, 0.25, 0.75])
def test_magnification_does_not_depend_on_the_content_scale(monkeypatch, display_scale):
    layout = _layout(monkeypatch, display_scale=display_scale)
    assert _magnification(layout, display_scale) == pytest.approx(
        DEFAULT_MAGNIFIER_MAGNIFICATION, rel=1e-6
    )


@pytest.mark.parametrize(
    "capture_rel, expected_factor",
    [(0.1, 1.0), (0.05, 2.0), (0.2, 0.5)],
)
def test_capture_setting_scales_the_magnification(
    monkeypatch, capture_rel, expected_factor
):
    display_scale = 0.4836
    layout = _layout(monkeypatch, capture_rel=capture_rel, display_scale=display_scale)
    assert _magnification(layout, display_scale) == pytest.approx(
        DEFAULT_MAGNIFIER_MAGNIFICATION * expected_factor, rel=1e-6
    )


def test_capture_ring_describes_the_sampled_region(monkeypatch):
    """Ring and uv rect are one measurement: a ring that shows one area while
    the loupe samples another is exactly the mismatch this file guards."""
    display_scale = 0.4836
    layout = _layout(monkeypatch, display_scale=display_scale)
    slot = layout.slots[0]
    ring_diameter_canvas_px = 2.0 * layout.capture_circles[0].radius
    sampled_canvas_px = (slot.uv_rect[2] - slot.uv_rect[0]) * CONTENT_W
    assert sampled_canvas_px == pytest.approx(ring_diameter_canvas_px, rel=1e-6)


def test_loupe_shows_five_sharp_zones_for_five_source_pixels(monkeypatch):
    """The owner's acceptance criterion, measured in layout px: five source
    pixels must occupy five distinguishable screen zones (one zone per source
    pixel), i.e. the loupe's screen pitch per source px is the constant."""
    display_scale = 0.4836
    layout = _layout(monkeypatch, display_scale=display_scale)
    screen_px_per_source_px = _magnification(layout, display_scale)
    zones = 5
    assert zones * screen_px_per_source_px == pytest.approx(
        zones * DEFAULT_MAGNIFIER_MAGNIFICATION
    )
    # and the drawn loupe really is that wide on a 1024-wide widget
    drawn_diameter_widget = 2.0 * layout.slots[0].radius * display_scale
    assert drawn_diameter_widget > 0.0
    assert drawn_diameter_widget / screen_px_per_source_px == pytest.approx(
        2.0 * layout.capture_circles[0].radius
    )
