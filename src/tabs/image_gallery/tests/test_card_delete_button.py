"""Card delete ✕ button: persistent red cross removes the card from the grid.

Reject (capsule ✕) only toggles the rejected flag; the top-right ✕ deletes
the card via ``remove_from_grid`` (file on disk stays) + HUD notice.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from PySide6.QtWidgets import QWidget

from tabs.image_gallery.models import GalleryItem
from tabs.image_gallery.ui.card import build_gallery_card


def _owner(items: list[GalleryItem]) -> SimpleNamespace:
    notes: list = []
    hud = SimpleNamespace(notify=lambda text, timeout_ms=2500: notes.append(text))
    owner = SimpleNamespace(
        state=SimpleNamespace(items=list(items), selected_paths=set(), selected_order=[]),
        _selection_hud=hud,
    )
    owner.notes = notes
    return owner


def _card(qtbot, item: GalleryItem, owner: SimpleNamespace):
    parent = QWidget()
    qtbot.addWidget(parent)
    card = build_gallery_card(item, parent=parent, owner=owner)
    card._test_parent = parent  # strong ref: qtbot tracks via weakref only
    parent.resize(400, 300)
    parent.show()
    card.show()
    return card


def _delete_button(card):
    btn = card.findChild(QWidget, "gallery_card_delete")
    assert btn is not None
    return btn


def _click(btn) -> None:
    try:
        btn.click()
    except Exception:
        btn.clicked.emit()


def test_delete_button_present_top_right(qtbot) -> None:
    """Every card carries the persistent delete ✕ at its top-right corner."""
    item = GalleryItem(path=Path("/gallery/a.png"), mtime_ns=1)
    card = _card(qtbot, item, _owner([item]))
    btn = _delete_button(card)
    assert btn.isVisible()
    pos = btn.pos()
    assert pos.x() + btn.width() <= card.width()
    assert pos.y() < card.height() // 2


def test_delete_button_hidden_while_rejected(qtbot) -> None:
    """One cross per corner: rejected cards show the toolkit ✕ badge instead."""
    from tabs.image_gallery.ui.card import update_gallery_card

    item = GalleryItem(path=Path("/gallery/a.png"), mtime_ns=1, rejected=True)
    card = _card(qtbot, item, _owner([item]))
    assert not _delete_button(card).isVisible()
    item.rejected = False
    update_gallery_card(card, item)
    assert _delete_button(card).isVisible()


def test_delete_button_removes_card_and_notifies(qtbot) -> None:
    """Clicking ✕ removes the card from state and names it in the HUD."""
    a = GalleryItem(path=Path("/gallery/a.png"), mtime_ns=1)
    b = GalleryItem(path=Path("/gallery/b.png"), mtime_ns=2)
    owner = _owner([a, b])
    card = _card(qtbot, a, owner)
    _click(_delete_button(card))
    assert [str(it.path) for it in owner.state.items] == [str(b.path)]
    assert owner.notes == ["Removed a.png"]
