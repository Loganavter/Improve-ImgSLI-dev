"""Quick Look strip cursor: arrows move it, Enter confirms it.

The overlay's arrows used to change the picture the moment they were pressed
(``_walk``), so reading a series was destructive — a keystroke you take back
with another one, and no way to look before you leap. Now:

* ``←``/``→`` (and the ``‹``/``›`` circles) move a **cursor** along the
  filmstrip: the thumb takes keyboard focus, so the app's own keyboard ring
  marks where the cursor is, and the strip scrolls it into view;
* ``Enter`` **confirms** — the picture follows, from the cursor's item
  (``commit_cursor``);
* ``↓`` hands the cursor to the action row (**Set as source** / **Reject** /
  **Delete**), ``↑`` brings it back to the strip — those controls were
  mouse-only while the overlay belonged to no navigation section;
* a thumb **click** still switches immediately: the mouse already names its
  target, so requiring a second confirmation there would be pointless.

The overlay registers itself as a ``NavigationManager`` **section** while it is
visible (``register`` / ``unregister`` from the show/hide lifecycle), so the
app's one keyboard model owns these keys instead of a private
``keyPressEvent`` — the shell's section routing and the control channel's
``nav_key``/``ui_nav_state`` tooling both see it, and arrows cannot fall through
to the gallery behind an open overlay.

Fail-open everywhere: a missing strip, a section registration failure or a dead
C++ handle leaves the overlay usable (and the legacy arrow behaviour is *not*
silently restored — the picture changes only on confirm).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from tabs.image_gallery.debug import gallery_debug as _dbg

#: Overlay attribute holding the cursor (kept beside ``_current_idx``, which
#: keeps meaning "the picture on screen").
CURSOR_ATTR = "_strip_cursor_idx"


def _reason(manager) -> Qt.FocusReason:
    """The app's focus-reason policy (mouse → no ring, keyboard → ring)."""
    try:
        if manager is not None:
            return manager.current_focus_reason()
    except Exception:
        pass
    return Qt.FocusReason.OtherFocusReason


def series_len(overlay) -> int:
    try:
        return len(getattr(overlay, "_series_items", None) or [])
    except Exception:
        return 0


def strip_buttons(overlay) -> list:
    try:
        return list(getattr(overlay, "_strip_buttons", None) or [])
    except Exception:
        return []


def cursor_index(overlay) -> int:
    """The cursor's index, clamped into the current series (0 when unknown)."""
    n = series_len(overlay)
    if n <= 0:
        return 0
    try:
        idx = int(getattr(overlay, CURSOR_ATTR, None) or 0)
    except Exception:
        idx = 0
    return max(0, min(idx, n - 1))


def thumb_widget(overlay, idx: int):
    """The live widget carrying thumb *idx*.

    ``_strip_buttons`` holds **containers** (``quicklook_strip_container_N``),
    not thumbs — focusing a container paints no ring, which is why the cursor
    was invisible and (after a rebuild) unfocusable. The thumb is the ``Button``
    named ``quicklook_strip_N`` inside its container; the container stays as a
    fallback for a partially built strip.
    """
    containers = strip_buttons(overlay)
    if not (0 <= int(idx) < len(containers)):
        return None
    container = containers[int(idx)]
    try:
        from sli_ui_toolkit.widgets import Button as _Button

        for child in container.findChildren(_Button):
            if child.objectName().startswith("quicklook_strip_"):
                return child
    except Exception:
        pass
    return container


def paint_cursor(overlay, idx: int | None = None) -> int:
    """Mark thumb *idx* with ``strip_cursor`` on the live widgets.

    Painted by the strip's own overlay painter (a dashed accent outline), so the
    cursor is visible without Qt focus — it survives the strip rebuild that
    follows every confirmed step, and it stays visible while the cursor is in the
    action row (the caret remembers what Enter would show).
    """
    idx = cursor_index(overlay) if idx is None else int(idx)
    for i in range(series_len(overlay)):
        widget = thumb_widget(overlay, i)
        if widget is None:
            continue
        try:
            widget.setProperty("strip_cursor", i == idx)
            widget.update()
        except Exception:
            continue
    return idx


def reapply_cursor(overlay) -> None:
    """Re-assert the cursor after a strip rebuild: marker + focus.

    Called from the strip's own per-populate sync point. Never steals focus from
    the action row (a background metrics pass may repopulate the panel while the
    user is on a button), and re-runs once more on the next tick because a
    rebuild can replace the thumb widgets after this call.
    """
    try:
        paint_cursor(overlay)
    except Exception:
        pass
    if zone_of(overlay) == "actions":
        return

    def _apply() -> None:
        widget = thumb_widget(overlay, cursor_index(overlay))
        if widget is None:
            return
        try:
            widget.setFocus(_reason(_manager()))
        except Exception:
            pass

    _apply()
    try:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, _apply)
    except Exception:
        pass


def set_cursor(overlay, idx: int, *, reason: Qt.FocusReason | None = None, reveal: bool = True) -> int:
    """Put the cursor on *idx*, show it (focus + scroll) and return it."""
    n = series_len(overlay)
    if n <= 0:
        return 0
    idx = max(0, min(int(idx), n - 1))
    try:
        setattr(overlay, CURSOR_ATTR, idx)
    except Exception:
        pass
    _remember_zone(overlay, "strip")
    paint_cursor(overlay, idx)
    thumb = thumb_widget(overlay, idx)
    if thumb is not None:
        try:
            thumb.setFocus(reason if reason is not None else _reason(None))
        except Exception:
            pass
    if reveal:
        try:
            from tabs.image_gallery.ui.quick_look.strip.rebuild import ensure_strip_visible

            ensure_strip_visible(overlay, idx)
        except Exception:
            pass
    return idx


def sync_cursor_to_current(overlay) -> int:
    """Follow the shown item (after a walk/commit/mouse click)."""
    try:
        current = int(getattr(overlay, "_current_idx", 0) or 0)
    except Exception:
        current = 0
    return set_cursor(overlay, current, reveal=False)


def move_cursor(overlay, delta: int, *, manager=None) -> int:
    """Walk the cursor ±*delta* along the strip (wraps, never re-binds)."""
    n = series_len(overlay)
    if n <= 0:
        return 0
    idx = (cursor_index(overlay) + int(delta)) % n
    idx = set_cursor(overlay, idx, reason=_reason(manager))
    _dbg("quick look cursor=%d/%d (picture still on _current_idx=%s)", idx, n,
         getattr(overlay, "_current_idx", "?"))
    return idx


def commit_cursor(overlay, *, manager=None) -> bool:
    """Confirm the cursor: re-bind the preview to its item. ``False`` = no-op."""
    n = series_len(overlay)
    if n <= 0:
        return False
    idx = cursor_index(overlay)
    try:
        current = int(getattr(overlay, "_current_idx", 0) or 0)
    except Exception:
        current = -1
    if idx == current:
        return False
    try:
        overlay._current_idx = idx
        items = list(getattr(overlay, "_series_items", None) or [])
        if 0 <= idx < len(items):
            overlay._current_item = items[idx]
    except Exception:
        return False
    # Re-bind the pixels but keep the user's wheel-zoom/pan across the step
    # (plan-ql-zoom-persist) — the same contract ``_walk`` honoured.
    try:
        from tabs.image_gallery.ui.quick_look.overlay_parts import populate as _populate_parts

        _populate_parts._populate(overlay, preserve_view=True)
    except Exception:
        try:
            overlay._populate()
        except Exception:
            return False
    _dbg("quick look commit cursor=%d/%d path=%s", idx, n, getattr(overlay, "_series_items", [])[idx]
         if 0 <= idx < n else "?")
    sync_cursor_to_current(overlay)
    return True


def action_row_buttons(overlay) -> list:
    """The bottom action row in tab order (Set as source / Reject / Delete)."""
    out: list = []
    for attr in ("_set_source_btn", "_reject_btn", "_delete_btn"):
        button = getattr(overlay, attr, None)
        try:
            if button is not None and button.isVisible() and button.isEnabled():
                out.append(button)
        except Exception:
            continue
    return out


#: Overlay attribute remembering which action-row button the cursor last sat on,
#: so ↑/↓ round-trips land where the user left.
ACTION_ATTR = "_nav_action_idx"


def action_index(overlay) -> int:
    """The action-row cursor's index, clamped into the row as it is now."""
    buttons = action_row_buttons(overlay)
    if not buttons:
        return 0
    try:
        idx = int(getattr(overlay, ACTION_ATTR, None) or 0)
    except Exception:
        idx = 0
    return max(0, min(idx, len(buttons) - 1))


def focus_action_row(overlay, *, manager=None, index: int | None = None) -> bool:
    """Hand the cursor to the action row (↓); *index* picks the button.

    The row has three controls (Set as source / Reject / Delete), so the cursor
    is an index, not a single landing spot: ``→``/``←`` walk it, ``↑`` leaves it,
    ``Enter`` activates the one under the cursor.
    """
    buttons = action_row_buttons(overlay)
    if not buttons:
        return False
    idx = action_index(overlay) if index is None else max(0, min(int(index), len(buttons) - 1))
    try:
        setattr(overlay, ACTION_ATTR, idx)
    except Exception:
        pass
    _remember_zone(overlay, "actions")
    try:
        buttons[idx].setFocus(_reason(manager))
    except Exception:
        return False
    _dbg("quick look action cursor=%d/%d", idx, len(buttons))
    return True


def move_action_cursor(overlay, delta: int, *, manager=None) -> int:
    """Walk the action row (clamped — a row of choices is not a carousel)."""
    buttons = action_row_buttons(overlay)
    if not buttons:
        return 0
    idx = max(0, min(action_index(overlay) + int(delta), len(buttons) - 1))
    focus_action_row(overlay, manager=manager, index=idx)
    return idx


def activate_action(overlay) -> bool:
    """Activate the action button under the cursor (Enter in the action row).

    The section claims Enter, so the button never gets its own activation
    keystroke — without this, Enter on **Set as source** confirmed the strip
    cursor instead of pressing the button (measured live 2026-10-17).
    """
    focused = focused_widget(overlay)
    for button in action_row_buttons(overlay):
        if button is focused:
            try:
                button.click()
                return True
            except Exception:
                return False
    return False


def focused_widget(overlay):
    """The overlay's own focus widget, even while its window is not OS-active.

    ``QApplication.focusWidget()`` reports ``None`` for a background window
    (the control channel drives the app that way), which would read as "strip"
    and send Enter to the wrong action.
    """
    try:
        focused = overlay.focusWidget()
        if focused is not None:
            return focused
    except Exception:
        pass
    return QApplication.focusWidget()


#: Overlay attribute remembering which zone owns the cursor. Focus alone cannot
#: answer it: anything that moves focus out of the panel (the control channel
#: re-anchors on the canvas before every injected key, a flyout opening, the
#: window re-activating) would otherwise read as "strip" and send Enter to the
#: wrong action — measured live 2026-10-17 (↓ into the row, then → walked the
#: filmstrip instead of the buttons).
ZONE_ATTR = "_nav_zone"


def _remember_zone(overlay, zone: str) -> None:
    try:
        setattr(overlay, ZONE_ATTR, zone)
    except Exception:
        pass


def remembered_zone(overlay) -> str:
    """The last zone the cursor was placed in (``"strip"`` until told otherwise)."""
    try:
        return "actions" if str(getattr(overlay, ZONE_ATTR, "") or "") == "actions" else "strip"
    except Exception:
        return "strip"


def _inside(container, widget) -> bool:
    try:
        return bool(widget is not None and (container is widget or container.isAncestorOf(widget)))
    except Exception:
        return False


def zone_of(overlay) -> str:
    """Which zone the keyboard cursor is in: ``"actions"`` or ``"strip"``.

    Live focus wins when it sits in one of the zones; otherwise the remembered
    zone answers (see :data:`ZONE_ATTR`).
    """
    focused = focused_widget(overlay)
    if focused is not None:
        for button in action_row_buttons(overlay):
            if button is focused:
                return "actions"
        for container in strip_buttons(overlay):
            if _inside(container, focused):
                return "strip"
    return remembered_zone(overlay)


def focus_strip(overlay, *, manager=None) -> bool:
    """Bring the cursor back to the strip (↑)."""
    n = series_len(overlay)
    if n <= 0:
        return False
    set_cursor(overlay, cursor_index(overlay), reason=_reason(manager))
    return True


class QuickLookNavSection:
    """Navigation section owning the Quick Look overlay while it is visible.

    ``owns`` claims the overlay and its whole subtree, so every key the shell
    would send into the panel is routed here first; ``navigate`` implements the
    cursor contract above. ``extra_keys`` claims Enter/Return so the manager
    routes the confirmation through ``navigate`` too (flyout-style sections do
    the same for Return/Escape); Escape is deliberately *not* claimed — the
    overlay's own close path stays as it was.
    """

    def __init__(self, overlay: QWidget) -> None:
        self._overlay = overlay

    def owns(self, widget) -> bool:  # noqa: ANN001 (duck-typed)
        overlay = self._overlay
        if widget is overlay:
            return True
        try:
            return bool(overlay.isAncestorOf(widget))
        except Exception:
            return False

    def navigate(self, key: int, widget) -> bool:  # noqa: ANN001
        overlay = self._overlay
        _dbg("quick look nav-section key=%s", Qt.Key(key).name)
        zone = zone_of(overlay)
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            delta = -1 if key == Qt.Key.Key_Left else 1
            if zone == "actions":
                move_action_cursor(overlay, delta, manager=_manager())
            else:
                move_cursor(overlay, delta, manager=_manager())
            return True
        if key == Qt.Key.Key_Down:
            if zone == "actions":
                return True  # one row here: nothing below it
            focus_action_row(overlay, manager=_manager())
            return True
        if key == Qt.Key.Key_Up:
            if zone == "actions":
                focus_strip(overlay, manager=_manager())
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if zone == "actions":
                activate_action(overlay)
            else:
                commit_cursor(overlay, manager=_manager())
            return True
        return False

    def focus_first(self, ref_x=None, *, reason: Qt.FocusReason = Qt.FocusReason.OtherFocusReason) -> bool:  # noqa: ANN001
        # The "first" item of this panel is the one on screen: landing the
        # cursor anywhere else would light a ring on a picture nobody asked for.
        try:
            current = int(getattr(self._overlay, "_current_idx", 0) or 0)
        except Exception:
            current = 0
        set_cursor(self._overlay, current, reason=reason)
        return True

    def focus_last(self, ref_x=None, *, reason: Qt.FocusReason = Qt.FocusReason.OtherFocusReason) -> bool:  # noqa: ANN001
        n = series_len(self._overlay)
        if n <= 0:
            return False
        set_cursor(self._overlay, n - 1, reason=reason)
        return True

    @property
    def extra_keys(self) -> frozenset:
        """Keys this section claims: Enter (confirm) and ←/→ (move the cursor).

        ←/→ must be listed here to *own* the strip walk: horizontal arrows are
        yielded to native delivery by default, so without them the overlay's own
        ``keyPressEvent`` is the only thing moving the cursor and the section
        never acts (measured live 2026-10-17 — cursor moved, no section trace).
        ``ToolbarRowsSection`` opts into Left/Right for the same reason.

        Must stay a **property**: every reader iterates the raw value
        (``NavigationManager.eventFilter``: ``key in getattr(spec, "extra_keys",
        frozenset())``), so a plain method raised
        ``TypeError: argument of type 'method' is not a container or iterable``
        inside the event filter on every ←/→ — reported live by the app's own
        diagnostics dialog.
        """
        return frozenset(
            {Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Return, Qt.Key.Key_Enter}
        )


def _manager():
    try:
        from sli_ui_toolkit.managers import NavigationManager

        return NavigationManager.get_instance()
    except Exception:
        return None


def register(overlay) -> None:
    """Make the overlay a navigation section (idempotent, fail-open)."""
    manager = _manager()
    if manager is None or overlay is None:
        return
    try:
        section = getattr(overlay, "_nav_section", None)
        if section is None:
            section = QuickLookNavSection(overlay)
            overlay._nav_section = section
        manager.register(overlay, section)
        sync_cursor_to_current(overlay)
    except Exception:
        pass


def unregister(overlay) -> None:
    """Drop the section again (idempotent, fail-open)."""
    manager = _manager()
    if manager is None or overlay is None:
        return
    try:
        manager.unregister(overlay)
    except Exception:
        pass


__all__ = [
    "ACTION_ATTR",
    "ZONE_ATTR",
    "CURSOR_ATTR",
    "QuickLookNavSection",
    "activate_action",
    "action_index",
    "action_row_buttons",
    "move_action_cursor",
    "remembered_zone",
    "zone_of",
    "commit_cursor",
    "cursor_index",
    "focus_action_row",
    "focus_strip",
    "focused_widget",
    "move_cursor",
    "register",
    "series_len",
    "set_cursor",
    "paint_cursor",
    "reapply_cursor",
    "strip_buttons",
    "sync_cursor_to_current",
    "thumb_widget",
    "unregister",
]
