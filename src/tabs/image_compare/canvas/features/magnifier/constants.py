"""Magnifier feature constants — owned by the magnifier canvas feature."""

from domain.types import Point

DEFAULT_MAGNIFIER_SIZE_RELATIVE = 0.4
DEFAULT_CAPTURE_SIZE_RELATIVE = 0.1

#: Loupe magnification, in SCREEN px per SOURCE px — the one number the eye
#: judges. The capture radius is DERIVED from the drawn diameter and this
#: value (``capture_radius = visible_radius / magnification``), so the loupe
#: shows this many screen px per source px whatever the window or image size.
#:
#: Before 2026-10-26 the capture radius was an independent fraction of the
#: content short edge, and because that ratio lived in *canvas* px while the
#: canvas is letterboxed (content scale 0.4836 on a live 1400x1000 pair) the
#: loupe really showed ``4.73 * 0.4836 = 2.29`` screen px per source px. At
#: that scale NEAREST/BILINEAR/LANCZOS differed by <= 29/255 on 17% of the
#: loupe's pixels and read to the owner as "the interpolation setting does
#: nothing live". Measured on a leased instance: a 7 px source cell showed as
#: 16 px; with this constant it shows as 35 px (5 screen px per source px),
#: i.e. five distinguishable sharp zones for five source pixels.
#:
#: ``capture_size_relative`` keeps its place as the user's control, but it now
#: scales the magnification RELATIVELY to this default (halve the captured
#: area -> double the loupe), so saved settings keep their ordering while the
#: drawn result is decided in one place.
DEFAULT_MAGNIFIER_MAGNIFICATION = 5.0
DEFAULT_CAPTURE_POS_RELATIVE = Point(0.5, 0.5)
DEFAULT_MAGNIFIER_OFFSET_RELATIVE = Point(0.0, -0.15)
DEFAULT_MAGNIFIER_SPACING_RELATIVE = 0.02

MIN_MAGNIFIER_SPACING_RELATIVE = 0.0
MAX_MAGNIFIER_SPACING_RELATIVE = 1.0
MIN_MAGNIFIER_SPACING_RELATIVE_FOR_COMBINE = 0.005

CAPTURE_THICKNESS_FACTOR = 0.35
MIN_CAPTURE_THICKNESS = 1
MAX_CAPTURE_THICKNESS = 4
MIN_MAG_BORDER_THICKNESS = 1
MAX_MAG_BORDER_THICKNESS = 4
