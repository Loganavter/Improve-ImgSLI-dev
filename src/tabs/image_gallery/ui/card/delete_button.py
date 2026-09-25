"""Card delete button — persistent red ✕ at the top-right (painter pipeline only)."""

from __future__ import annotations

from pathlib import Path


def wire_card_delete_button(card, owner) -> None:  # type: ignore[no-untyped-def]
    """Attach the persistent red ✕ (real removal from the grid) to *card*.

    Reject (capsule ✕) only toggles the rejected flag; this button deletes
    the card via ``remove_from_grid`` (file on disk stays). Survives pool
    recycling: the handler resolves the live item/owner on every click.
    """
    from sli_ui_toolkit.managers import scaled_px
    from sli_ui_toolkit.widgets import Button

    from tabs.image_gallery.ui.card.hover import _after_card_action, _capsule_icon_color

    try:
        from tabs.image_gallery.ui.card import GALLERY_CARD_W
    except Exception:
        GALLERY_CARD_W = 250

    try:
        size = int(scaled_px(20))
        margin = int(scaled_px(6))
    except Exception:
        size, margin = 20, 6
    try:
        width = int(card.width()) or int(GALLERY_CARD_W)
    except Exception:
        width = int(GALLERY_CARD_W)
    try:
        btn = Button(text="✕", variant="ghost", parent=card)
    except Exception:
        return
    btn.setObjectName("gallery_card_delete")
    try:
        btn.setFixedSize(size, size)
    except Exception:
        pass
    try:
        btn.move(width - size - margin, margin)
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
        btn.raise_()
    except Exception:
        pass
