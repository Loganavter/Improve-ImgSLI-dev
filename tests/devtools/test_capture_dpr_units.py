"""Capture path: DPR enters exactly once, and the units are NAMED.

``core/control/capture.compose_rhi_frames`` multiplied the canvas anchor and
size by the DPR **and** painted into a ``QPixmap`` that already carries its own
``devicePixelRatio`` (a ``QPainter`` on such a pixmap works in
device-independent coordinates). Measured on a real ``QPainter``: a canvas
meant for device ``(200,100)-(600,300)`` at DPR=2 landed in
``(400,200)-(1198,598)`` — double the offset and double the size.

Every assertion carries the geometry it means (device vs logical), because "a
number is a number" is exactly what produced the bug.

Falsification story: on the pre-fix tree the paint test reports red at device
``(250,150)`` (its paint starts at ``400``) and red at ``(650,350)``
(double-scaled paint reaches it).

Run: ``QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 -m pytest
tests/devtools/test_capture_dpr_units.py -q -o addopts=""``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from core.control import capture as capture_mod

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


# ---------------------------------------------------------------------------
# compose_rhi_frames: the painter target rect is DEVICE-INDEPENDENT
# ---------------------------------------------------------------------------


class _FakeCanvas:
    """Duck-typed ``QRhiWidget``: the compositing path touches only these."""

    def __init__(self, *, anchor, size, image, visible: bool = True) -> None:
        self._anchor = anchor
        self._size = size
        self._image = image
        self._visible = visible

    def isVisible(self) -> bool:  # noqa: N802 - Qt name
        return self._visible

    def width(self) -> int:
        return self._size[0]

    def height(self) -> int:
        return self._size[1]

    def mapToGlobal(self, _point):  # noqa: N802 - Qt name
        from PySide6.QtCore import QPoint

        return QPoint(*self._anchor)

    def grabFramebuffer(self):  # noqa: N802 - Qt name
        return self._image


class _FakeTarget:
    """A widget wearing only ``findChildren`` + ``mapFromGlobal``."""

    def __init__(self, canvases) -> None:
        self._canvases = list(canvases)

    def findChildren(self, _cls):  # noqa: N802 - Qt name
        return list(self._canvases)

    def mapFromGlobal(self, point):  # noqa: N802 - Qt name
        return point


def _solid(size, color):
    from PySide6.QtGui import QColor, QImage

    image = QImage(size[0], size[1], QImage.Format.Format_RGBA8888)
    image.fill(QColor(*color))
    return image


def test_compose_rhi_frames_paints_at_the_canvas_device_rect_on_hidpi() -> None:
    """A 200x100 logical canvas at DPR=2 fills device (200,100)-(600,300).

    ``QPixmap(1200, 800)`` with dpr 2 is a 600x400 logical grab. The canvas
    sits at logical ``(100, 50)`` and is ``200x100`` logical, so its device
    rect is ``(200,100)-(600,300)``: one offset, one size, one DPR.
    """
    from PySide6.QtGui import QColor, QPixmap

    _app()
    pixmap = QPixmap(1200, 800)
    pixmap.setDevicePixelRatio(2.0)
    pixmap.fill(QColor(0, 0, 0))
    canvas = _FakeCanvas(
        anchor=(100, 50),
        size=(200, 100),
        image=_solid((400, 200), (255, 0, 0)),
    )

    assert capture_mod.compose_rhi_frames(_FakeTarget([canvas]), pixmap) == 1

    image = pixmap.toImage()

    def red(x_device: int, y_device: int) -> int:
        return image.pixelColor(x_device, y_device).red()

    # Inside the intended device rect (x offset, y offset, both slightly in).
    assert red(250, 150) > 200, "the frame did not land at the canvas anchor"
    assert red(350, 150) > 200, "the frame did not land at the canvas anchor (y)"
    # Far corner of the intended rect: proves the SIZE is the logical one.
    assert red(550, 250) > 200, "the frame is smaller than the canvas"
    # Outside the intended rect but inside the double-scaled one the pre-fix
    # code painted: 2x offset + 2x size reached device (400,200)-(1198,598).
    assert red(650, 350) < 50, "the canvas frame was scaled by DPR twice"
    assert red(1000, 700) < 50, "the canvas frame was scaled by DPR twice (far)"


def test_compose_rhi_frames_skips_a_canvas_outside_the_logical_grab() -> None:
    """The grab rect is logical too: ``deviceIndependentSize``, not ``width()``.

    A 600x400 logical grab (1200x800 device px at DPR=2). The canvas sits at
    logical x=650 — off the grab — although 650 looks "inside" a 1200-wide
    device-number rect. Counting it as painted is wrong; painting it is
    invisible only because the painter clips.
    """
    from PySide6.QtGui import QColor, QPixmap

    _app()
    pixmap = QPixmap(1200, 800)
    pixmap.setDevicePixelRatio(2.0)
    pixmap.fill(QColor(0, 0, 0))
    canvas = _FakeCanvas(
        anchor=(650, 50),
        size=(100, 100),
        image=_solid((200, 200), (0, 255, 0)),
    )

    assert capture_mod.compose_rhi_frames(_FakeTarget([canvas]), pixmap) == 0
