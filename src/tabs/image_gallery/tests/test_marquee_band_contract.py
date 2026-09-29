"""Marquee band behavior contract (Lane A, phase A1).

Pins the gallery marquee's update/finish plumbing against the stable public
API (``on_rect_update`` / ``on_rect_finish`` / ``event_filter`` /
``host_mouse_press``) so the A2 in-paint refactor can prove no semantic
drift: these tests pass on the overlay path AND on the in-paint path.

Mapping/pixel tests for the new path live in the A2 section below (they
exercise ``MarqueeState``/``MarqueeHost`` content-space identity and only
pass post-refactor).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent

from tabs.image_gallery.ui import marquee as _marquee


def _card(geom: QRect):
    return SimpleNamespace(geometry=lambda: QRect(geom))


def _view():
    applied: list[set] = []
    cards = {
        "a.png": _card(QRect(10, 10, 100, 100)),
        "b.png": _card(QRect(200, 10, 100, 100)),
    }
    view = SimpleNamespace(
        _items=[SimpleNamespace(path=Path("a.png")), SimpleNamespace(path=Path("b.png"))],
        _marquee_additive=False,
        _marquee_base=set(),
        _owner=None,
        owner=None,
        _on_marquee_preview=None,
        apply_selection=lambda paths: applied.append(set(paths)),
    )
    view.card_for = lambda p: cards.get(str(p))
    return view, applied


def _owner_view():
    """View delegating commits to an owner (production shape)."""
    painted: list[set] = []
    grid = SimpleNamespace(apply_selection=lambda paths: painted.append(set(paths)))
    state = SimpleNamespace(selected_paths=set())
    owner = SimpleNamespace(state=state, grid_view=grid)
    view = SimpleNamespace(
        _items=[SimpleNamespace(path=Path("a.png")), SimpleNamespace(path=Path("b.png"))],
        _marquee_additive=False,
        _marquee_base=set(),
        _owner=owner,
        owner=None,
        _on_marquee_preview=None,
        apply_selection=lambda paths: painted.append(set(paths)),
    )
    view.card_for = lambda p: None  # force fixed-grid fallback path? no — no cards
    return view, owner, painted


def test_update_dispatches_preview_paths() -> None:
    view, applied = _view()
    _marquee.on_rect_update(view, QRect(0, 0, 150, 150))  # hits card A only
    assert len(applied) == 1
    assert {str(p) for p in applied[0]} == {"a.png"}


def test_update_additive_unions_base() -> None:
    view, applied = _view()
    view._marquee_additive = True
    view._marquee_base = {Path("b.png")}
    _marquee.on_rect_update(view, QRect(0, 0, 150, 150))  # hits A; preview = base | hit
    assert len(applied) == 1
    assert {str(p) for p in applied[0]} == {"a.png", "b.png"}


def test_finish_commits_via_owner_with_paths_and_flag() -> None:
    view, owner, painted = _owner_view()
    # Owner path needs live card geometry: stub card_for via fixed grid is
    # bypassed here — give the view real card geometry instead.
    cards = {
        "a.png": _card(QRect(10, 10, 100, 100)),
        "b.png": _card(QRect(200, 10, 100, 100)),
    }
    view.card_for = lambda p: cards.get(str(p))
    view._marquee_additive = False
    _marquee.on_rect_finish(view, QRect(0, 0, 350, 150))  # hits A+B
    assert {str(p) for p in owner.state.selected_paths} == {"a.png", "b.png"}


def test_finish_empty_non_additive_clears_owner() -> None:
    """COMMIT-EMPTY: shrink-to-empty replaces with the hit set (empty)."""
    view, owner, painted = _owner_view()
    owner.state.selected_paths = {Path("a.png")}
    view._marquee_additive = False
    _marquee.on_rect_finish(view, QRect())
    assert set(owner.state.selected_paths) == set()


def test_finish_empty_additive_keeps_selection() -> None:
    view, owner, painted = _owner_view()
    owner.state.selected_paths = {Path("a.png")}
    view._marquee_additive = True
    _marquee.on_rect_finish(view, QRect())
    assert {str(p) for p in owner.state.selected_paths} == {"a.png"}


def test_tiny_drag_finishes_empty_non_additive() -> None:
    """1x1 band over empty space hits nothing → non-additive commit clears."""
    view, owner, painted = _owner_view()
    cards = {
        "a.png": _card(QRect(10, 10, 100, 100)),
        "b.png": _card(QRect(200, 10, 100, 100)),
    }
    view.card_for = lambda p: cards.get(str(p))
    owner.state.selected_paths = {Path("a.png")}
    view._marquee_additive = False
    _marquee.on_rect_finish(view, QRect(0, 0, 1, 1))
    assert set(owner.state.selected_paths) == set()


def _mouse_event(etype, local: QPoint, global_pos: QPoint, button, buttons):
    return QMouseEvent(
        etype,
        QPointF(local),
        QPointF(global_pos),
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )


def test_release_passes_through_while_finishing(qtbot) -> None:
    """Hover-loss contract: LeftButton release returns False (pass-through),
    moves are consumed while dragging. Holds on both gesture generations.
    """
    from tabs.image_gallery.ui.grid_view import GalleryGridView

    view = GalleryGridView()
    qtbot.addWidget(view)
    view.resize(800, 600)
    view.show()
    qtbot.wait(50)
    host = view.items_host
    origin = QPoint(host.width() - 30, host.height() - 30)
    assert host.childAt(origin) is None
    press = _mouse_event(
        QEvent.Type.MouseButtonPress, origin, host.mapToGlobal(origin),
        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
    )
    assert _marquee.host_mouse_press(view, press) is True
    gesture = view._marquee_gesture
    assert gesture is not None
    assert bool(getattr(gesture, "active", False)) is True

    moved_at = QPoint(origin.x() - 200, origin.y() - 100)
    move = _mouse_event(
        QEvent.Type.MouseMove, moved_at, host.mapToGlobal(moved_at),
        Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
    )
    assert gesture.eventFilter(host, move) is True  # consumed while dragging

    release = _mouse_event(
        QEvent.Type.MouseButtonRelease, moved_at, host.mapToGlobal(moved_at),
        Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
    )
    assert gesture.eventFilter(host, release) is False  # pass-through, still finishes
