"""Gallery list row — one rich row (thumb + name + badges + artifacts + VLM).

Split from ``list_view.py`` per FILE_SIZE_POLICY (>500 lines): the row is
self-contained (content mapping + events), the view owns sections/layout.
Row emits ``activated(path, additive)`` on LMB press and
``context_requested(path)`` on context-menu event — same contract as grid
cards (``on_toggle``/``on_context_menu``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from sli_ui_toolkit.managers import scaled_px
from sli_ui_toolkit.widgets import Label

from tabs.image_gallery.models import GalleryItem

ROW_HEIGHT = 48
THUMB_W = 56
THUMB_H = 36


def _badges_text(item: GalleryItem) -> str:
    parts: list[str] = []
    try:
        if getattr(item, "rejected", False):
            parts.append("✕")
    except Exception:
        pass
    try:
        if getattr(item, "is_best", False):
            parts.append("★")
    except Exception:
        pass
    try:
        rank = getattr(item, "rank", None)
        if rank is not None:
            parts.append(f"R{int(rank)}")
    except Exception:
        pass
    try:
        crown = getattr(item, "crown_rank", None)
        if crown is not None and not getattr(item, "is_best", False):
            parts.append(f"C{int(crown)}")
    except Exception:
        pass
    return " ".join(parts)


def _artifacts_text(item: GalleryItem) -> str:
    """Compact artifact summary: F<n> flagged / M<n> mild / OK / …."""
    try:
        artifacts = getattr(item, "artifacts", None) or {}
        flagged = mild = 0
        for _aid, sev in dict(artifacts).items():
            try:
                s = sev.value.lower() if hasattr(sev, "value") else str(sev).lower()
            except Exception:
                s = "clean"
            if s == "flagged":
                flagged += 1
            elif s == "mild":
                mild += 1
        if flagged:
            return f"F{flagged}"
        if mild:
            return f"M{mild}"
        try:
            from tabs.image_gallery.models import AnalysisStatus

            if getattr(item, "analysis_status", None) == AnalysisStatus.DONE:
                return "OK"
        except Exception:
            pass
        return "…"
    except Exception:
        return "…"


def _vlm_text(item: GalleryItem) -> str:
    """Compact VLM state: err > tie… > tie-done/brief > ''."""
    try:
        if getattr(item, "vlm_tie_error", None) or getattr(item, "vlm_brief_error", None):
            return "err"
        if getattr(item, "vlm_tie_pending", False):
            return "tie…"
        if getattr(item, "vlm_tie_result", None) is not None:
            return "tie✓"
        try:
            status = str(getattr(item, "vlm_brief_status", None) or "none")
        except Exception:
            status = "none"
        if status not in ("none", ""):
            return "brief"
    except Exception:
        pass
    return ""


def _tooltip_text(item: GalleryItem) -> str:
    """Same tooltip parts as grid cards (widget._refresh_tooltip parity)."""
    parts = [item.name]
    try:
        if item.analysis is not None:
            parts.append(item.analysis.description)
            if item.analysis.tags:
                parts.append(", ".join(item.analysis.tags))
    except Exception:
        pass
    try:
        if item.analysis_error:
            parts.append(item.analysis_error)
    except Exception:
        pass
    return "\n".join(str(p) for p in parts if p)


class _RowSelectBar(QWidget):
    """3px accent bar shown on selected rows (no QSS — explicit paint)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(scaled_px(3))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def _accent(self) -> QColor:
        # Frozen chain via the card helper (dots._accent_color):
        # gallery.accent.bar → accent → light/dark fallback. No color
        # literals here — contracts ban hardcoded QColor outside theme
        # infra (test_no_hardcoded_qcolor) and get_color() outside it
        # (test_no_manual_theming).
        try:
            from tabs.image_gallery.ui.card.dots import _accent_color

            return _accent_color()
        except Exception:
            return QColor()

    def paintEvent(self, event) -> None:  # noqa: N802
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._accent())
            r = self.rect().adjusted(0, scaled_px(6), 0, -scaled_px(6))
            p.drawRoundedRect(r, 1.5, 1.5)
            p.end()
        except Exception:
            pass


class GalleryListRow(QWidget):
    """One rich row: thumb + name + badges + artifacts + VLM.

    Emits ``activated(path, additive)`` on LMB press and
    ``context_requested(path)`` on context-menu event — same contract as
    grid cards (``on_toggle``/``on_context_menu``).
    """

    activated = Signal(object, bool)
    context_requested = Signal(object)

    def __init__(
        self,
        item: GalleryItem,
        parent: QWidget | None = None,
        *,
        on_toggle: Callable | None = None,
        on_context_menu: Callable | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("GalleryListRow")
        self._item = item
        self._path = item.path
        try:
            self.setProperty("gallery_path", str(item.path))
        except Exception:
            pass
        if callable(on_toggle):
            try:
                self.activated.connect(lambda p, a: on_toggle(p, a))
            except Exception:
                pass
        if callable(on_context_menu):
            try:
                self.context_requested.connect(lambda p: on_context_menu(p))
            except Exception:
                pass

        lay = QHBoxLayout(self)
        lay.setContentsMargins(scaled_px(4), scaled_px(4), scaled_px(8), scaled_px(4))
        lay.setSpacing(scaled_px(8))

        self._select_bar = _RowSelectBar(self)
        self._select_bar.hide()
        lay.addWidget(self._select_bar)

        self._thumb = QLabel(self)
        self._thumb.setObjectName("gallery_row_thumb")
        self._thumb.setFixedSize(scaled_px(THUMB_W), scaled_px(THUMB_H))
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._thumb)

        self._name = Label(item.name, pixel_size=12, parent=self)
        self._name.setObjectName("gallery_row_name")
        try:
            self._name.setBold(True)
        except Exception:
            pass
        self._name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay.addWidget(self._name, 1)

        self._badges = Label("", pixel_size=11, parent=self)
        self._badges.setObjectName("gallery_row_badges")
        lay.addWidget(self._badges)

        self._artifacts = Label("", pixel_size=11, parent=self)
        self._artifacts.setObjectName("gallery_row_artifacts")
        lay.addWidget(self._artifacts)

        self._vlm = Label("", pixel_size=11, parent=self)
        self._vlm.setObjectName("gallery_row_vlm")
        lay.addWidget(self._vlm)

        self.setFixedHeight(scaled_px(ROW_HEIGHT))
        self.refresh(item)

    @property
    def gallery_path(self) -> Path:
        return self._path

    def refresh(self, item: GalleryItem) -> None:
        """Repaint row content from *item* (thumb + texts + tooltip)."""
        self._item = item
        self._path = item.path
        try:
            self.setProperty("gallery_path", str(item.path))
        except Exception:
            pass
        # Thumbnail (QPixmap or gray placeholder).
        try:
            pix = getattr(item, "thumbnail", None)
            if pix is not None and not pix.isNull():
                self._thumb.setPixmap(
                    pix.scaled(
                        scaled_px(THUMB_W),
                        scaled_px(THUMB_H),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                ph = QPixmap(scaled_px(THUMB_W), scaled_px(THUMB_H))
                try:
                    from tabs.image_gallery.ui.card.visuals import _token_qcolor

                    fill = _token_qcolor("gallery.stats.background", "#3c3c3c")
                except Exception:
                    fill = QColor()
                ph.fill(fill)
                self._thumb.setPixmap(ph)
        except Exception:
            pass
        try:
            self._name.setText(item.name)
        except Exception:
            pass
        try:
            self._badges.setText(_badges_text(item))
        except Exception:
            pass
        try:
            self._artifacts.setText(_artifacts_text(item))
        except Exception:
            pass
        try:
            self._vlm.setText(_vlm_text(item))
        except Exception:
            pass
        try:
            self.setToolTip(_tooltip_text(item))
        except Exception:
            pass

    def set_selected(self, selected: bool) -> None:
        try:
            if bool(selected):
                self._select_bar.show()
            else:
                self._select_bar.hide()
        except Exception:
            pass

    def mousePressEvent(self, event) -> None:  # noqa: N802
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                mods = event.modifiers()
                additive = bool(
                    mods & Qt.KeyboardModifier.ControlModifier
                    or mods & Qt.KeyboardModifier.ShiftModifier
                )
                self.activated.emit(self._path, additive)
                event.accept()
                return
        except Exception:
            pass
        try:
            super().mousePressEvent(event)
        except Exception:
            pass

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        try:
            self.context_requested.emit(self._path)
            event.accept()
        except Exception:
            pass
