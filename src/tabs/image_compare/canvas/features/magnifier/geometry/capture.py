"""ONE owner for the loupe's capture geometry (magnification invariant).

Why this module exists: the drawn loupe (``geometry/layout_plan.py``) and the
scene graph (``scene/build.py``) used to compute the capture radius from
``capture_size_relative`` independently — same formula, two owners. That was
harmless while the number was a free ratio, and became a lie the moment the
magnification became an invariant: the paint showed one area while the scene
(hit-testing, guides, ``get_canvas_scene``) described another. Measured
2026-10-26: the scene read reported the legacy 50 canvas px capture while the
renderer sampled the derived radius.

The rule (owner decision 2026-10-26, option A): the loupe shows
``DEFAULT_MAGNIFIER_MAGNIFICATION`` SCREEN px per SOURCE px. The captured area
is therefore DERIVED from the drawn disk and the content scale, never the other
way round:

    capture_radius = (size_radius_canvas * display_scale) / magnification

``capture_size_relative`` stays the user's control, but it scales the
magnification RELATIVELY to the default (halving the captured area doubles the
loupe), so saved settings keep their ordering while the geometry is decided in
one place.
"""

from __future__ import annotations

import math

from tabs.image_compare.canvas.features.magnifier.constants import (
    DEFAULT_CAPTURE_SIZE_RELATIVE,
    DEFAULT_MAGNIFIER_MAGNIFICATION,
)


def resolve_magnifier_magnification(capture_size_relative: float) -> float:
    """Screen px per source px this loupe shows (>= the default floor)."""
    capture_rel = float(capture_size_relative or 0.0)
    if capture_rel <= 1e-6:
        return float(DEFAULT_MAGNIFIER_MAGNIFICATION)
    return float(DEFAULT_MAGNIFIER_MAGNIFICATION) * (
        float(DEFAULT_CAPTURE_SIZE_RELATIVE) / capture_rel
    )


def resolve_magnifier_capture_radius(
    *,
    size_relative: float,
    capture_size_relative: float,
    pix_w: float,
    pix_h: float,
    display_scale: float = 1.0,
) -> tuple[float, float]:
    """Return ``(capture_radius_canvas_px, magnification)``.

    ``pix_w``/``pix_h`` are the content size in canvas px (the space the loupe
    is authored in); ``display_scale`` is canvas px -> widget px
    (``runtime_state._content_sr``), the coefficient the old canvas-space ratio
    was missing — without it a letterboxed canvas silently divided the real
    magnification by the content scale (2.29x instead of 4.73x on a live
    1400x1000 pair, which is why the interpolation choice was invisible).
    """
    target_max = math.sqrt(max(1.0, float(pix_w)) * max(1.0, float(pix_h)))
    magnifier_radius_canvas = (float(size_relative) * target_max) / 2.0
    visible_radius_widget = magnifier_radius_canvas * max(
        1e-6, float(display_scale or 1.0)
    )
    magnification = max(
        1e-6, resolve_magnifier_magnification(capture_size_relative)
    )
    return visible_radius_widget / magnification, magnification


def capture_size_relative_for_radius(radius: float, pix_w: float, pix_h: float) -> float:
    """The relative size the position clamp expects for a derived radius."""
    return (2.0 * float(radius)) / float(max(1, min(int(pix_w), int(pix_h))))
