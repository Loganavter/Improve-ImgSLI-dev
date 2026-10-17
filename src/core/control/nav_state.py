"""Keyboard-navigation state and key delivery for the control channel.

The app's keyboard cursor is **not** ``QApplication.focusWidget()``. Arrow keys
belong to ``sli_ui_toolkit``'s ``NavigationManager``, which keeps an ordered list
of *sections* (title bar → tab strip → session picker → a tab's toolbar/grid
rows) and hands a key to the section whose ``owns()`` accepts the focused
widget, delegating across section boundaries on a boundary key. Whole surfaces
(the Quick Look overlay, flyouts) instead handle keys in their own
``keyPressEvent`` and are not sections at all.

``press_keys`` cannot judge that model: it aims one event at one widget — the
right tool for a canvas, whose shortcuts are not in the focus chain — and the
events it injects carry no focus attribution, so the sections never engage and a
client cannot tell "the key reached the control" from "the key went nowhere".

This module answers the two questions the model raises, over the live app:

* :func:`nav_state_payload` — what the navigation model *is*: the ordered
  sections, the Qt focus widget, the last keyboard-granted widget, and every
  open in-window overlay with the children that Qt *could* focus but that no
  section owns (the honest "a keyboard cannot reach this" signal).
* :func:`deliver_nav_keys` — what a key *does*: send it to the widget the user's
  key would reach (optionally focusing a named element first with the app's own
  focus-reason policy), then report which layer took it and how focus moved.

Both are live-only and GUI-thread only (the control server dispatches there).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QEventLoop, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QWidget

from .discovery import MethodError, parse_key_sequence
from .elements.inventory import Element, collect_elements, rect_list, screen_rect_of
from .elements.resolve import resolve_element

#: Overlay children reported in one call (a Quick Look overlay owns dozens).
MAX_OVERLAY_CHILDREN = 80


def _nav_manager():
    """The toolkit ``NavigationManager`` singleton, or ``None`` (import-guarded)."""
    try:
        from sli_ui_toolkit.managers import NavigationManager

        return NavigationManager.get_instance()
    except Exception:
        return None


def _sections_of(manager) -> list[tuple[Any, Any]]:
    """Ordered ``(owner, section)`` pairs.

    Prefers a public ``sections()`` accessor when the toolkit grows one and
    falls back to the manager's own list, so the control channel never guesses
    the navigation graph from widget types.
    """
    if manager is None:
        return []
    accessor = getattr(manager, "sections", None)
    if callable(accessor):
        try:
            return [(owner, spec) for owner, spec in accessor()]
        except Exception:
            pass
    try:
        return [(owner, spec) for owner, spec in (getattr(manager, "_sections", None) or ())]
    except Exception:
        return []


def _owner_of(manager, widget: QWidget | None) -> str | None:
    """Class name of the section that owns *widget*, or ``None``."""
    if widget is None or manager is None:
        return None
    for owner, spec in _sections_of(manager):
        try:
            if callable(getattr(spec, "owns", None)) and spec.owns(widget):
                return type(spec).__name__
        except Exception:
            continue
    return None


def _focus_policy_name(widget: QWidget) -> str:
    try:
        policy = widget.focusPolicy()
    except Exception:
        return "?"
    try:
        return policy.name
    except Exception:
        return str(policy)


def _element_map(registry: Any) -> dict[int, Element]:
    """``id(widget)`` → its inventory element (so rows can carry element ids)."""
    try:
        collected = collect_elements(registry=registry, include_disabled=True)
    except Exception:
        return {}
    out: dict[int, Element] = {}
    for element in collected:
        out.setdefault(id(element.widget), element)
    return out


def _row(
    widget: QWidget | None,
    elements: dict[int, Element],
    manager,
) -> dict[str, Any] | None:
    """One widget's honest description, or ``None`` for "nothing focused"."""
    if widget is None:
        return None
    element = elements.get(id(widget))
    try:
        geometry = widget.rect()
        screen_rect: list[int] | None = rect_list(screen_rect_of(widget, geometry))
    except Exception:
        screen_rect = None
    return {
        "widget": type(widget).__name__,
        "object_name": widget.objectName() if hasattr(widget, "objectName") else "",
        "label": element.label if element is not None else "",
        "role": element.role if element is not None else None,
        "element_id": element.id if element is not None else None,
        "focus_policy": _focus_policy_name(widget),
        "owned_by_section": _owner_of(manager, widget),
        "enabled": bool(element.enabled) if element is not None else None,
        "visible": bool(element.visible) if element is not None else None,
        "screen_rect": screen_rect,
    }


def _focusables(root: QWidget) -> list[QWidget]:
    """Widgets under *root* that Qt would let a Tab reach (any area, visible)."""
    out: list[QWidget] = []
    try:
        children = root.findChildren(QWidget)
    except Exception:
        return out
    for child in children:
        try:
            if child.focusPolicy() == Qt.FocusPolicy.NoFocus:
                continue
            if not child.isVisibleTo(root) or not child.isEnabled():
                continue
            if child.width() <= 0 or child.height() <= 0:
                continue
        except Exception:
            continue
        out.append(child)
    return out


def _overlays(window: QWidget | None, elements: dict[int, Element], manager) -> list[dict[str, Any]]:
    """Visible in-window overlays (Quick Look, clean review, flyouts) with their
    focusable children and whether any navigation section owns them."""
    if window is None:
        return []
    rows: list[dict[str, Any]] = []
    try:
        children = window.findChildren(QWidget)
    except Exception:
        return rows
    for child in children:
        if not type(child).__name__.endswith("Overlay"):
            continue
        try:
            if not child.isVisible() or child.isWindow():
                continue
        except Exception:
            continue
        focusables = _focusables(child)
        row = _row(child, elements, manager) or {}
        row.update(
            {
                "children_total": len(focusables),
                "children_shown": min(len(focusables), MAX_OVERLAY_CHILDREN),
                "children_truncated": len(focusables) > MAX_OVERLAY_CHILDREN,
                "focused_child": _row(QApplication.focusWidget(), elements, manager)
                if QApplication.focusWidget() is not None
                and child.isAncestorOf(QApplication.focusWidget())
                else None,
                "children": [
                    _row(item, elements, manager) for item in focusables[:MAX_OVERLAY_CHILDREN]
                ],
            }
        )
        rows.append(row)
    return rows


def _modality(manager) -> dict[str, Any]:
    payload: dict[str, Any] = {"last_input_was_keyboard": None, "focus_reason": None}
    if manager is None:
        return payload
    try:
        payload["last_input_was_keyboard"] = bool(manager.last_input_was_keyboard())
    except Exception:
        pass
    try:
        payload["focus_reason"] = manager.current_focus_reason().name
    except Exception:
        pass
    return payload


def nav_state_payload(*, registry: Any, app: Any, window: Any) -> dict[str, Any]:
    """The live navigation model: sections, focus, modality, open overlays."""
    manager = _nav_manager()
    elements = _element_map(registry)
    qt_focus = QApplication.focusWidget()
    last_keyboard = None
    try:
        last_keyboard = manager.last_keyboard_focus() if manager is not None else None
    except Exception:
        last_keyboard = None
    sections = [
        {
            "index": index,
            "section": type(spec).__name__,
            "owner": type(owner).__name__,
            "extra_keys": sorted(
                _key_names(getattr(spec, "extra_keys", frozenset()))
            ),
        }
        for index, (owner, spec) in enumerate(_sections_of(manager))
    ]
    return {
        "source": "live",
        "modality": _modality(manager),
        "focus": _row(qt_focus, elements, manager),
        "last_keyboard_focus": _row(last_keyboard, elements, manager),
        "owner_section": _owner_of(manager, qt_focus),
        "sections": sections,
        "sections_count": len(sections),
        "overlays": _overlays(window, elements, manager),
    }


def _key_names(keys) -> list[str]:
    out: list[str] = []
    for key in keys or ():
        try:
            out.append(Qt.Key(key).name)
        except Exception:
            out.append(str(key))
    return out


def _focus_anchor(
    *, registry: Any, app: Any, window: Any, element_id: str | None, manager
) -> tuple[QWidget | None, bool]:
    """Where a user's key would land; ``element_id`` focuses it first.

    Returns ``(widget, focused_by_us)``. Focusing routes through the app's own
    reason policy (``NavigationManager.current_focus_reason``) so the keyboard
    ring behaves as it would for a real key press.
    """
    if element_id:
        element = resolve_element(registry, element_id)
        reason = Qt.FocusReason.OtherFocusReason
        try:
            if manager is not None:
                reason = manager.current_focus_reason()
        except Exception:
            pass
        try:
            element.widget.setFocus(reason)
        except Exception as exc:
            raise MethodError(
                f"could not focus {element_id!r}: {exc}",
                "the element may not accept keyboard focus (check its focus policy)",
            )
        if app is not None:
            try:
                app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
            except Exception:
                pass
        return element.widget, True
    focused = QApplication.focusWidget()
    if focused is not None:
        return focused, False
    try:
        if manager is not None:
            last = manager.last_keyboard_focus()
            if last is not None:
                return last, False
    except Exception:
        pass
    return (window if isinstance(window, QWidget) else None), False


def _snapshot(manager, elements: dict[int, Element]) -> dict[str, Any]:
    focus = QApplication.focusWidget()
    last = None
    try:
        last = manager.last_keyboard_focus() if manager is not None else None
    except Exception:
        last = None
    return {
        "focus": focus,
        "focus_row": _row(focus, elements, manager),
        "last_keyboard_focus": last,
        "owner": _owner_of(manager, focus),
    }


def _verdict(before: dict[str, Any], after: dict[str, Any]) -> str:
    """Which layer took the key — derived, never guessed.

    ``section:<name>`` — the section that owns the focus changed, or the
    keyboard-granted widget changed (the navigation system acted);
    ``focus`` — Qt focus moved inside the same section (a widget took it);
    ``unhandled`` — nothing observable changed, i.e. a real key would be lost.
    """
    if after["owner"] != before["owner"]:
        return f"section:{after['owner'] or before['owner'] or 'none'}"
    if after["last_keyboard_focus"] is not before["last_keyboard_focus"]:
        return f"section:{after['owner'] or 'none'}"
    if after["focus"] is not before["focus"]:
        return "focus"
    return "unhandled"


def deliver_nav_keys(
    *,
    registry: Any,
    app: Any,
    window: Any,
    keys: str | None,
    element_id: str | None = None,
) -> dict[str, Any]:
    """Send *keys* the way the running app receives a real key press.

    The event goes to the widget that actually holds what a user's key would
    reach — the Qt focus widget (or the element named by ``element_id``, which
    is focused first) — and travels through the app's own event filters, so
    ``NavigationManager``'s sections and each surface's ``keyPressEvent`` take
    part in the decision exactly as they do for a human. Nothing is aimed at a
    single widget behind the routing (that is ``press_keys target=``).
    """
    sequence = parse_key_sequence(keys)
    manager = _nav_manager()
    elements = _element_map(registry)
    anchor, focused_by_us = _focus_anchor(
        registry=registry,
        app=app,
        window=window,
        element_id=element_id,
        manager=manager,
    )
    if anchor is None:
        raise MethodError(
            "no live widget to receive keys",
            "focus a window first (e.g. open a tab), then retry",
        )
    steps: list[dict[str, Any]] = []
    for key, modifiers, label in sequence:
        before = _snapshot(manager, elements)
        for event_type in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            event = QKeyEvent(event_type, key, modifiers)
            try:
                QApplication.sendEvent(anchor, event)
            except Exception as exc:
                raise MethodError(
                    f"could not deliver {label!r}: {exc}",
                    "the live window may be shutting down",
                )
        if app is not None:
            try:
                app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
            except Exception:
                pass
        after = _snapshot(manager, elements)
        steps.append(
            {
                "key": label,
                "delivered_to": _row(anchor, elements, manager),
                "handled": _verdict(before, after),
                "focus_before": before["focus_row"],
                "focus_after": after["focus_row"],
                "owner_before": before["owner"],
                "owner_after": after["owner"],
            }
        )
    return {
        "source": "live",
        "keys": [label for _key, _mods, label in sequence],
        "count": len(sequence),
        "anchor": _row(anchor, elements, manager),
        "focus_is_ours": focused_by_us,
        "focus_after": _row(QApplication.focusWidget(), elements, manager),
        "steps": steps,
    }


class NavMethodsMixin:
    """``ui_nav_state`` / ``nav_key``, mixed into ``ControlHandlers``."""

    def ui_nav_state(self, params: dict[str, Any]) -> dict[str, Any]:
        return nav_state_payload(
            registry=self._registry(),  # type: ignore[attr-defined]
            app=getattr(self, "_app", None),
            window=getattr(self, "_window", None),
        )

    def nav_key(self, params: dict[str, Any]) -> dict[str, Any]:
        return deliver_nav_keys(
            registry=self._registry(),  # type: ignore[attr-defined]
            app=getattr(self, "_app", None),
            window=getattr(self, "_window", None),
            keys=params.get("keys"),
            element_id=params.get("anchor") or params.get("from") or params.get("element_id"),
        )


__all__ = ["NavMethodsMixin", "deliver_nav_keys", "nav_state_payload"]
