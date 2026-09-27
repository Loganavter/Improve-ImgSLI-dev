"""S2-8: list view toggle, series sections, rich rows, selection parity."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent

from tabs.image_gallery.models import GalleryItem
from tabs.image_gallery.ui.list_row import (
    _artifacts_text,
    _badges_text,
    _vlm_text,
)
from tabs.image_gallery.ui.list_view import GalleryListView
from tabs.image_gallery.widget import ImageGalleryWidget


def _items(*names: str) -> list[GalleryItem]:
    return [
        GalleryItem(path=Path(f"/gallery/{n}"), mtime_ns=i + 1)
        for i, n in enumerate(names)
    ]


def _press(widget, button: Qt.MouseButton):
    ev = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        widget.rect().center().toPointF(),
        button,
        button,
        Qt.KeyboardModifier.NoModifier,
    )
    widget.mousePressEvent(ev)


def test_view_toggle_switches_stack(qtbot) -> None:
    w = ImageGalleryWidget()
    qtbot.addWidget(w)
    items = _items("a.png", "b.png")
    w.rebuild_grid(items)
    assert w._content_stack.currentWidget() is w._grid_view
    w._on_view_toggled(True)
    assert w._content_stack.currentWidget() is w._list_view
    assert len(w._list_view._rows_by_path) == 2
    w._on_view_toggled(False)
    assert w._content_stack.currentWidget() is w._grid_view


def test_toggle_empty_stays_empty(qtbot) -> None:
    w = ImageGalleryWidget()
    qtbot.addWidget(w)
    w.rebuild_grid([])
    w._on_view_toggled(True)
    assert w._content_stack.currentWidget() is w._empty_state


def test_series_sections_and_collapse(qtbot) -> None:
    view = GalleryListView()
    qtbot.addWidget(view)
    items = _items("a.png", "b.png", "c.png")
    view.rebuild(items)
    view.set_series([items[:2]], hub_names=["hub1"], collapsed={})
    assert view._series is not None and len(view._series) == 1
    # 2 cluster rows + UNGROUPED tail (c.png).
    assert len(view._rows_by_path) == 3
    assert view.row_for(items[0].path) is not None
    view._toggle_collapse(0)
    assert view._collapsed == {0: True}
    # Cluster hidden — only the tail row left.
    assert len(view._rows_by_path) == 1
    assert view.row_for(items[2].path) is not None


def test_rich_row_texts() -> None:
    assert _badges_text(_items("a.png")[0]) == ""
    it = _items("a.png")[0]
    it.is_best = True
    it.rank = 3
    assert "★" in _badges_text(it) and "R3" in _badges_text(it)
    rej = _items("b.png")[0]
    rej.rejected = True
    assert "✕" in _badges_text(rej)
    assert _artifacts_text(_items("c.png")[0]) == "…"
    assert _vlm_text(_items("d.png")[0]) == ""
    tie = _items("e.png")[0]
    tie.vlm_tie_pending = True
    assert _vlm_text(tie) == "tie…"


def test_row_click_emits_toggle(qtbot) -> None:
    view = GalleryListView()
    qtbot.addWidget(view)
    items = _items("a.png", "b.png")
    got: list = []
    view.configure(
        on_toggle=lambda p, additive=False: got.append((p, additive)),
        on_context_menu=None,
    )
    view.rebuild(items)
    row = view.row_for(items[0].path)
    assert row is not None
    _press(row, Qt.MouseButton.LeftButton)
    assert len(got) == 1 and str(got[0][0]) == str(items[0].path)


def test_selection_sync_grid_and_list(qtbot) -> None:
    w = ImageGalleryWidget()
    qtbot.addWidget(w)
    items = _items("a.png", "b.png")
    w.rebuild_grid(items)
    w._render_gallery_selection([str(items[0].path)])
    row = w._list_view.row_for(items[0].path)
    # isHidden (not isVisible): ancestors may hide the whole stack offscreen.
    assert row is not None and not row._select_bar.isHidden()
    other = w._list_view.row_for(items[1].path)
    assert other is not None and other._select_bar.isHidden()


def test_refresh_row_updates_content(qtbot) -> None:
    view = GalleryListView()
    qtbot.addWidget(view)
    items = _items("a.png")
    view.rebuild(items)
    row = view.row_for(items[0].path)
    assert row is not None and row._name.text() == "a.png"
    items[0].rank = 7
    view.refresh_row(items[0])
    assert "R7" in row._badges.text()


def test_append_items_lands_in_tail(qtbot) -> None:
    view = GalleryListView()
    qtbot.addWidget(view)
    items = _items("a.png", "b.png", "c.png")
    view.rebuild(items)
    view.set_series([items[:2]], hub_names=["h"], collapsed={})
    extra = _items("d.png")
    view.append_items(extra)
    assert view.row_for(extra[0].path) is not None
    assert len(view._ungrouped) == 2  # c.png + d.png


def test_marquee_wiring_selects_rows(qtbot) -> None:
    """Empty-area drag on the list host selects intersecting rows."""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent

    from tabs.image_gallery.ui import marquee as _marquee

    view = GalleryListView()
    qtbot.addWidget(view)
    view.show()
    qtbot.waitExposed(view)
    items = _items("a.png", "b.png", "c.png")
    view.rebuild(items)
    qtbot.wait(20)
    # Marquee hit-test sees rows through the card_for alias.
    assert view.card_for(items[0].path) is view.row_for(items[0].path)
    assert len(view._cards_by_path) == 3
    host = view.items_host
    full = host.rect()
    assert full.height() > 0
    hits = _marquee.paths_for_rect(view, full)
    assert {str(p) for p in hits} == {str(it.path) for it in items}
    # Empty-area press starts the band gesture (no owner → view fallback).
    empty_pt = host.rect().bottomLeft().toPointF() + QPointF(2, -2)
    ev = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        empty_pt,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    assert host.childAt(empty_pt.toPoint()) is None
    assert view.eventFilter(host, ev) is True
    assert view._marquee_gesture is not None
