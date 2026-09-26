"""Raw Qt input firehose for the gallery (DEBUGGING.md rule 5).

The causal tracer only records dispatches; hover never dispatches, so it
is invisible there by construction (rule 7 blindness). This stream taps the
event boundary instead: every mouse press/release/move plus Enter/Leave,
with receiver + position. Gated by ``IMGSLI_GALLERY_EVENTS_DEBUG``,
default off, session-only, never consumed (filter always returns False)
and never mixed into the curated ``[gallery-debug]`` stream.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject

_WATCHED_TYPES = frozenset(
    {
        QEvent.Type.MouseButtonPress,
        QEvent.Type.MouseButtonDblClick,
        QEvent.Type.MouseButtonRelease,
        QEvent.Type.MouseMove,
        QEvent.Type.Enter,
        QEvent.Type.Leave,
    }
)


def _describe(watched) -> str:
    try:
        cls = type(watched).__name__
    except Exception:
        cls = "?"
    try:
        name = watched.objectName()
    except Exception:
        name = ""
    extra = ""
    try:
        gp = watched.property("gallery_path")
        if gp:
            extra = f" gallery={gp}"
    except Exception:
        pass
    return f"{cls}:{name}{extra}" if name or extra else cls


def _pos_of(event) -> str:
    for attr in ("globalPosition", "globalPos", "pos"):
        try:
            p = getattr(event, attr, None)
            v = p() if callable(p) else p
            if v is not None:
                try:
                    return f"({int(v.x())},{int(v.y())})"
                except Exception:
                    return str(v)
        except Exception:
            continue
    return "?"


class _EventsFirehose(QObject):
    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        try:
            if event.type() not in _WATCHED_TYPES:
                return False
            from tabs.image_gallery.debug import gallery_event

            buttons = ""
            try:
                b = event.buttons()
                buttons = f" buttons={int(b)}" if int(b) else ""
            except Exception:
                pass
            gallery_event(
                "%s recv=%s pos=%s%s",
                event.type().name,
                _describe(watched),
                _pos_of(event),
                buttons,
            )
        except Exception:
            pass
        return False


def install_events_firehose() -> bool:
    """Install the app-wide firehose once. Returns True when active."""
    try:
        from PySide6.QtWidgets import QApplication

        from tabs.image_gallery.debug import gallery_events_enabled

        if not gallery_events_enabled():
            return False
        app = QApplication.instance()
        if app is None:
            return False
        if bool(getattr(app, "_gallery_events_firehose", False)):
            return True
        filt = _EventsFirehose(app)
        app.installEventFilter(filt)
        app._gallery_events_firehose = True  # type: ignore[attr-defined]
        app._gallery_events_filter = filt  # type: ignore[attr-defined]
        return True
    except Exception:
        return False
