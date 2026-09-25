"""Card delete button — round red-✕ badge overhanging the top-right corner.

The button CANNOT be a child of the card: the card clips children to its
own rect (verified: a QLabel child paints 0 px outside the card, 44 px on a
plain host). It lives on the card's host instead and is pinned to the card
corner via an event filter (Move/Resize/Show/Hide/ParentChange) — the same
relative-pinning idea as HTML absolute-in-relative, done manually because
the grid pool reparents cards.

Visibility is hover-only with a hover-intent delay: leaving the card
schedules the hide ~200 ms out so the cursor can travel onto the overhang
half (which sits outside the card rect and would otherwise flicker); the
button's own hover cancels the pending hide.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QEvent, QTimer

#: Hide delay after leaving the card/button (hover-intent window, ms).
_DELETE_HIDE_DELAY_MS = 200


class _CardDeletePin(QObject):
    """Keeps a host-level delete ✕ pinned to its card's overhang corner."""

    def __init__(self, card, btn, size: int) -> None:
        super().__init__(btn)
        self._card = card
        self._btn = btn
        self._size = int(size)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        try:
            if watched is self._card and event.type() in (
                QEvent.Type.Move,
                QEvent.Type.Resize,
                QEvent.Type.Show,
                QEvent.Type.Hide,
                QEvent.Type.ParentChange,
            ):
                sync_card_delete_button(self._card)
        except Exception:
            pass
        return False


class _DeleteHoverFilter(QObject):
    """Hover-intent for the delete ✕ itself (cancels the card-leave hide)."""

    def __init__(self, card, btn) -> None:
        super().__init__(btn)
        self._card = card
        self._btn = btn

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        try:
            if watched is self._btn:
                if event.type() == QEvent.Type.Enter:
                    try:
                        self._card._gallery_delete_hovered = True  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    cancel_delete_hide(self._card)
                    sync_card_delete_button(self._card)
                elif event.type() == QEvent.Type.Leave:
                    try:
                        self._card._gallery_delete_hovered = False  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    schedule_delete_hide(self._card)
        except Exception:
            pass
        return False


def cancel_delete_hide(card) -> None:
    """Invalidate a pending hover-intent hide (fail-open)."""
    try:
        card._gallery_delete_hide_token = int(getattr(card, "_gallery_delete_hide_token", 0) or 0) + 1  # type: ignore[attr-defined]
    except Exception:
        pass


def schedule_delete_hide(card, ms: int = _DELETE_HIDE_DELAY_MS) -> None:
    """Hide the delete ✕ after *ms* unless cancelled (fail-open)."""
    try:
        tok = int(getattr(card, "_gallery_delete_hide_token", 0) or 0) + 1
        card._gallery_delete_hide_token = tok  # type: ignore[attr-defined]
    except Exception:
        return

    def _fire(t=tok) -> None:
        try:
            if int(getattr(card, "_gallery_delete_hide_token", 0) or 0) != t:
                return
            btn = getattr(card, "_gallery_delete_btn", None)
            if btn is not None:
                btn.hide()
        except Exception:
            pass

    try:
        QTimer.singleShot(int(ms), _fire)
    except Exception:
        pass


def sync_card_delete_button(card) -> None:
    """Reposition/hide the card's delete ✕ to match the card (fail-open).

    Visible only while the card (or the button itself) is hovered, the card
    sits on the button's host, and the item is not rejected (the toolkit
    rejected ✕ badge owns the corner there — one cross per corner).
    """
    try:
        btn = getattr(card, "_gallery_delete_btn", None)
        filt = getattr(card, "_gallery_delete_pin", None)
        if btn is None or filt is None:
            return
        import shiboken6

        if not shiboken6.isValid(btn):
            return
        try:
            size = int(filt._size)
        except Exception:
            size = 20
        host = btn.parent()
        try:
            in_host = card.parent() is host and host is not None
        except Exception:
            in_host = False
        try:
            shown = bool(card.isVisibleTo(host)) if in_host else False
        except Exception:
            shown = False
        try:
            hovered = bool(getattr(card, "_gallery_delete_hovered", False))
        except Exception:
            hovered = False
        try:
            item = getattr(card, "_gallery_item", None)
            rejected = bool(getattr(item, "rejected", False))
        except Exception:
            rejected = False
        if not (in_host and shown and hovered) or rejected:
            try:
                btn.hide()
            except Exception:
                pass
            return
        try:
            pos = card.pos()
            btn.move(pos.x() + card.width() - size // 2, pos.y() - size // 2)
        except Exception:
            pass
        try:
            btn.show()
        except Exception:
            pass
        try:
            btn.raise_()
        except Exception:
            pass
    except Exception:
        pass


def wire_card_delete_button(card, owner) -> None:  # type: ignore[no-untyped-def]
    """Attach the hover-only round delete ✕ (real removal) to *card*.

    Reject (capsule ✕) only toggles the rejected flag; this button deletes
    the card via ``remove_from_grid`` (file on disk stays). Survives pool
    recycling: the handler resolves the live item/owner on every click, and
    the pin filter re-hides the button while the card sits in the pool.
    """
    from PySide6.QtGui import QColor

    from sli_ui_toolkit.managers import scaled_px
    from sli_ui_toolkit.widgets import Button

    from tabs.image_gallery.ui.card.hover import _after_card_action, _capsule_icon_color

    try:
        size = int(scaled_px(20))
    except Exception:
        size = 20
    try:
        host = card.parentWidget()
    except Exception:
        host = None
    if host is None:
        # No host to overhang from — fall back to an in-card button.
        try:
            host = card
        except Exception:
            return
    try:
        # Round badge: radius = half of the 20px design size; solid white
        # fill always (ghost alone is transparent idle and unreadable over
        # photos) + hairline border + red ✕.
        btn = Button(text="✕", variant="ghost", corner_radius=10, parent=host)
    except Exception:
        return
    btn.setObjectName("gallery_card_delete")
    try:
        btn.setFixedSize(size, size)
    except Exception:
        pass
    try:
        btn.set_override_bg_color(QColor("#ffffff"))
    except Exception:
        pass
    try:
        from tabs.image_gallery.ui.card.visuals import _card_border_color

        btn.setBorderColor(_card_border_color())
    except Exception:
        try:
            btn.setBorderColor(QColor("#e2e4e8"))
        except Exception:
            pass
    try:
        color = _capsule_icon_color("reject")
        if color is not None:
            btn.setForegroundColor(color)
    except Exception:
        pass
    try:
        btn.setToolTip("Remove from view")
    except Exception:
        pass
    try:
        btn.hide()
    except Exception:
        pass

    def _on_delete(_checked=False, c=card) -> None:
        actual_owner = owner if owner is not None else getattr(c, "_gallery_owner", None)
        if actual_owner is None:
            try:
                win = c.window()
                actual_owner = getattr(win, "_gallery_controller", None) or getattr(win, "_gallery_owner", None)
            except Exception:
                actual_owner = None
        item = getattr(c, "_gallery_item", None)
        path = getattr(item, "path", None) if item is not None else None
        if path is None:
            try:
                path = Path(str(c.property("gallery_path") or ""))
            except Exception:
                return
        try:
            from tabs.image_gallery.use_cases import triage as _triage

            ok = bool(_triage.remove_from_grid(actual_owner, path))
        except Exception:
            return
        if not ok:
            return
        try:
            _after_card_action(c, actual_owner, f"Removed {Path(path).name}")
        except Exception:
            pass

    try:
        btn.clicked.connect(_on_delete)
    except Exception:
        pass
    try:
        card._gallery_delete_btn = btn  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        card._gallery_delete_hovered = False  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        pin = _CardDeletePin(card, btn, size)
        card._gallery_delete_pin = pin  # type: ignore[attr-defined]
        card.installEventFilter(pin)
    except Exception:
        pass
    try:
        hover_filt = _DeleteHoverFilter(card, btn)
        card._gallery_delete_hover_filter = hover_filt  # type: ignore[attr-defined]
        btn.installEventFilter(hover_filt)
    except Exception:
        pass
    try:
        card.destroyed.connect(btn.deleteLater)
    except Exception:
        pass
    sync_card_delete_button(card)
