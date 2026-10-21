"""Wheel delivery through the control surface (``ui_wheel``, mcp-c-019).

The surface had no wheel primitive: zoom on the canvases and every scroll view
could only be driven by leaving the control channel for ``xdotool``. These
tests pin the delivery contract — notches of 120 angle units, Qt-like
propagation when a widget ignores the event, and the honest
``accepted``/``delivered_to`` answer.
"""

from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QWidget


class _AcceptsWheel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.events: list[QWheelEvent] = []

    def wheelEvent(self, event):  # noqa: N802 - Qt spelling
        self.events.append(event)
        event.accept()


class _IgnoresWheel(QWidget):
    def wheelEvent(self, event):  # noqa: N802 - Qt spelling
        event.ignore()


class _IgnoresWheelChild(_IgnoresWheel):
    pass


def _element(widget):
    return SimpleNamespace(widget=widget, rect=widget.rect(), id="stub", target="QWidget")


def test_wheel_element_delivers_one_notch_and_reports_the_target(qapp):
    from core.control.elements.interaction import wheel_element

    widget = _AcceptsWheel()
    result = wheel_element(_element(widget), steps=1)

    assert result["accepted"] is True
    assert result["delivered_to"] == "_AcceptsWheel"
    assert result["angle_delta"] == [0, 120]
    assert len(widget.events) == 1
    assert widget.events[0].angleDelta().y() == 120


def test_wheel_element_bubbles_to_a_parent_that_accepts(qapp):
    from core.control.elements.interaction import wheel_element

    parent = _AcceptsWheel()
    child = _IgnoresWheelChild(parent)
    child.resize(50, 50)
    result = wheel_element(_element(child), steps=-1)

    assert result["accepted"] is True
    assert result["delivered_to"] == "_AcceptsWheel"
    assert result["angle_delta"] == [0, -120]
    assert len(parent.events) == 1


def test_wheel_element_reports_a_widget_nobody_takes_it_from(qapp):
    from core.control.elements.interaction import wheel_element

    widget = _IgnoresWheel()
    result = wheel_element(_element(widget), steps=2)

    assert result["accepted"] is False
    assert result["delivered_to"] == "_IgnoresWheel"
    assert result["angle_delta"] == [0, 240]


def test_wheel_element_horizontal_axis_and_modifiers(qapp):
    from core.control.elements.interaction import wheel_element

    widget = _AcceptsWheel()
    result = wheel_element(
        _element(widget),
        steps=1,
        horizontal=True,
        modifiers=Qt.KeyboardModifier.ControlModifier,
    )

    assert result["angle_delta"] == [120, 0]
    assert widget.events[0].angleDelta().x() == 120
    assert widget.events[0].modifiers() & Qt.KeyboardModifier.ControlModifier


def test_wheel_element_count_repeats_the_notch(qapp):
    from core.control.elements.interaction import wheel_element

    widget = _AcceptsWheel()
    wheel_element(_element(widget), steps=1, count=3)
    assert len(widget.events) == 3


def test_control_surface_exposes_ui_wheel():
    """The method is reachable, declared as a tool, and answered live-only."""
    import sys
    from pathlib import Path

    from core.control.handlers import METHODS

    assert "ui_wheel" in METHODS

    repo_root = Path(__file__).resolve().parents[2]
    mcp_dir = repo_root / "mcp-server"
    if str(mcp_dir) not in sys.path:
        sys.path.insert(0, str(mcp_dir))
    from app import catalog as mcp_catalog
    from app.backend import AppBackend

    spec = next(t for t in mcp_catalog.TOOLS if t["name"] == "ui_wheel")
    assert spec["handler"] == "ui_wheel"
    assert spec["inputSchema"]["required"] == ["id"]
    assert callable(getattr(AppBackend, "ui_wheel", None))
