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

from PySide6.QtCore import QObject, QEvent


def widget_contains_cursor(widget) -> bool:
    """True when the live cursor sits over *widget* (fail-open False)."""
    try:
        if widget is None:
            return False
        import shiboken6

        if not shiboken6.isValid(widget):
            return False
        from PySide6.QtGui import QCursor

        # rect() is widget-local — the matching frame for mapFromGlobal.
        return bool(widget.rect().contains(widget.mapFromGlobal(QCursor.pos())))
    except Exception:
        return False


def card_delete_contains_cursor(card) -> bool:
    """True when the cursor sits over the card's delete ✕ (fail-open False)."""
    try:
        return widget_contains_cursor(getattr(card, "_gallery_delete_btn", None))
    except Exception:
        return False


def hide_card_delete_button(card) -> None:
    """Hide the card's delete ✕ immediately (fail-open)."""
    try:
        btn = getattr(card, "_gallery_delete_btn", None)
        if btn is not None:
            btn.hide()
    except Exception:
        pass


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
    """Hover for the delete ✕ itself.

    Hover counts over "card OR badge" (CSS :hover semantics): leaving the
    badge toward the card keeps it (the card Enter is imminent); leaving
    anywhere else hides immediately — same tick as the capsule.
    """

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
                    sync_card_delete_button(self._card)
                    _log_hover("delete hover enter", self._card)
                elif event.type() == QEvent.Type.Leave:
                    try:
                        self._card._gallery_delete_hovered = False  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    over_card = widget_contains_cursor(self._card)
                    if not over_card:
                        hide_card_delete_button(self._card)
                    _log_hover(f"delete hover leave over_card={over_card}", self._card)
        except Exception:
            pass
        return False


def _log_hover(msg: str, card) -> None:
    """One-line hover trace (env-gated, fail-open)."""
    try:
        from tabs.image_gallery.debug import gallery_debug as _dbg

        _dbg(
            "%s card=%s",
            msg,
            getattr(getattr(card, "_gallery_item", None), "path", "?"),
        )
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
        # Transition-only trace: steady states stay silent.
        try:
            was = bool(btn.isVisible())
        except Exception:
            was = False
        if not (in_host and shown and hovered) or rejected:
            try:
                btn.hide()
            except Exception:
                pass
            if was:
                _log_hover(
                    f"delete hide in_host={in_host} shown={shown} hovered={hovered} rejected={rejected}",
                    card,
                )
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
        if not was:
            _log_hover(
                f"delete show in_host={in_host} shown={shown} hovered={hovered} rejected={rejected}",
                card,
            )
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
        # Round badge: radius = half of the 20px design size (solid fill +
        # border applied below; ghost alone is transparent idle).
        btn = Button(text="✕", variant="ghost", corner_radius=10, parent=host)
    except Exception:
        return
    btn.setObjectName("gallery_card_delete")
    try:
        btn.setFixedSize(size, size)
    except Exception:
        pass
    # Inverted badge style (mirrors the toolkit rejected ✕ badge): filled
    # danger circle + white ✕. Reads on any photo; ghost alone is
    # transparent idle and unreadable.
    try:
        color = _capsule_icon_color("reject")
    except Exception:
        color = None
    try:
        from PySide6.QtGui import QColor as _QC

        danger = color if color is not None else _QC(217, 48, 37)
    except Exception:
        danger = None
    try:
        if danger is not None:
            btn.set_override_bg_color(danger)
        else:
            btn.set_override_bg_color(QColor("#d93025"))
    except Exception:
        pass
    try:
        if danger is not None:
            btn.setBorderColor(danger)
    except Exception:
        pass
    try:
        btn.setForegroundColor(QColor("#ffffff"))
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
