"""Ask AI flyout (A3) — one scope-aware ask surface.

A toolkit ``BaseFlyout`` with a ``CustomLineEdit`` (pre-filled, overridable
default prompt: ``Tab`` accepts it, ``Enter`` sends) and a result pane marked
"AI read, unverified". Advisory only: the flyout renders text, it never
mutates rank/selection/store. All async work is dispatched by the controller
(``GalleryController.ask_ai_question``); this widget is pure surface.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QWidget

from sli_ui_toolkit.managers import scaled_px
from sli_ui_toolkit.widgets import BaseFlyout, CustomLineEdit, Label


class AskAiFlyout(BaseFlyout):
    """Free-form question + AI result, anchored to a card or series header."""

    flyout_group = "gallery_ask_ai"

    submitted = Signal(str)
    closed = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._default_prompt = "Summary"
        self.content_layout.setContentsMargins(
            scaled_px(12), scaled_px(12), scaled_px(12), scaled_px(12)
        )
        self.content_layout.setSpacing(scaled_px(8))

        self._title = Label("Ask AI", pixel_size=13, bold=True, parent=self)
        self._scope = Label("", pixel_size=11, parent=self)
        self._edit = CustomLineEdit(parent=self)
        self._edit.setPlaceholderText(self._default_prompt)
        self._edit.setMinimumWidth(scaled_px(300))
        try:
            self._edit.setClearButtonEnabled(True)
        except Exception:
            pass
        self._edit.returnPressed.connect(self._emit_submit)
        self._edit.installEventFilter(self)
        self._result = Label("", pixel_size=12, word_wrap=True, parent=self)
        self._result.setMinimumWidth(scaled_px(300))
        try:
            self._result.setMaximumWidth(scaled_px(460))
        except Exception:
            pass
        self._status = Label("", pixel_size=11, parent=self)

        for widget in (self._title, self._scope, self._edit, self._result, self._status):
            self.content_layout.addWidget(widget)

    # -- interaction --------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt name)
        # Tab accepts the grayed default prompt (else it is just a placeholder
        # and the user must retype it). Enter always sends.
        if obj is self._edit and event.type() == QEvent.Type.KeyPress:
            try:
                if event.key() == Qt.Key.Key_Tab and not self._edit.text().strip():
                    self._edit.setText(self._default_prompt)
                    self._edit.selectAll()
                    return True
            except Exception:
                pass
        return super().eventFilter(obj, event)

    def _emit_submit(self) -> None:
        try:
            question = self._edit.text().strip() or self._default_prompt
        except Exception:
            question = self._default_prompt
        self.submitted.emit(question)

    def open_for(
        self,
        anchor: QWidget,
        *,
        scope_label: str = "",
        default_prompt: str = "Summary",
        title: str = "Ask AI",
    ) -> None:
        """Reset + show under *anchor*; focus lands in the question field."""
        self._default_prompt = str(default_prompt or "Summary")
        self._title.setText(str(title or "Ask AI"))
        self._scope.setText(str(scope_label or ""))
        self._edit.setText("")
        self._edit.setPlaceholderText(self._default_prompt)
        self._edit.setReadOnly(False)
        self._result.setText("")
        self._status.setText("")
        try:
            self._edit.setFocus()
        except Exception:
            pass
        try:
            self.show_aligned(
                anchor,
                anchor_point="bottom-left",
                flyout_point="top-left",
                offset=scaled_px(8),
                animation="slide-fade",
                animation_axis="vertical",
            )
        except Exception:
            try:
                self.show_aligned(anchor)
            except Exception:
                pass

    # -- state (called by the controller) -----------------------------------

    def set_busy(self, busy: bool) -> None:
        try:
            self._edit.setReadOnly(bool(busy))
        except Exception:
            pass
        self._status.setText("Thinking…" if busy else "")

    def show_result(self, text: str, *, backend: str = "", cached: bool = False) -> None:
        badge = "AI read, unverified"
        if backend:
            badge += f" · {backend}"
        if cached:
            badge += " · cached"
        self._result.setText(str(text or ""))
        self._status.setText(badge)

    def show_error(self, message: str) -> None:
        self._result.setText("")
        self._status.setText(str(message or "AI could not answer."))

    def restore_focus_on_hide(self) -> bool:
        return False

    def hideEvent(self, event) -> None:  # noqa: N802 (Qt name)
        super().hideEvent(event)
        try:
            self.closed.emit()
        except Exception:
            pass


__all__ = ["AskAiFlyout"]
