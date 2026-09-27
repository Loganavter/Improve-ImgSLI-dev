"""Gallery list view — row-based alternative to the grid.

S2-8 stub implementation (plan_mockup_parity_2026-09-22:22,
design_parity_audit:106): flat series sections with collapsible headers and
rich rows (thumbnail + name + triage badges + artifacts + VLM state).

Public surface mirrors ``GalleryGridView`` so ``ImageGalleryWidget`` drives
both views through the same calls: ``configure``, ``rebuild``/``set_series``,
``apply_selection``, ``row_for``, ``refresh_row(s)``, ``append_items``.
Selection/triage state lives on the widget/controller — this view only
paints rows and emits ``on_toggle``/``on_context_menu`` like grid cards do.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sli_ui_toolkit.managers import scaled_px
from sli_ui_toolkit.widgets import Button, Label

from tabs.image_gallery.models import GalleryItem
from tabs.image_gallery.ui.list_row import GalleryListRow


def _series_header_text(index: int, hub: str | None, count: int) -> str:
    """Same header text as grid series headers (grid_view parity)."""
    if hub:
        return f"SERIES {index + 1} · {hub} · {count} VARIANTS"
    return f"SERIES {index + 1} · {count} images"


class GalleryListView(QWidget):
    """Scrollable row list with series sections (grid API parity).

    Sections mirror the grid: clusters ≥2 get ``SERIES i`` headers (same
    text, collapsible), the rest lands in an ``UNGROUPED`` tail. Flat
    pools (``series=None``) render rows with no headers.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GalleryListView")
        self._items: list[GalleryItem] = []
        self._rows_by_path: dict[str, GalleryListRow] = {}
        self._selection: set[str] = set()
        self._on_toggle = None
        self._on_context_menu = None
        self._series: list[list[GalleryItem]] | None = None
        self._ungrouped: list[GalleryItem] = []
        self._hub_names: list[str | None] = []
        self._collapsed: dict[int, bool] = {}
        # Marquee gesture state (marquee module is duck-typed: items_host,
        # scroll_area, _items, apply_selection, card_for/_cards_by_path).
        self._marquee_gesture = None
        self._marquee_additive = False
        self._marquee_base: set[str] = set()
        try:
            from tabs.image_gallery.ui.card.visuals import gallery_selection_accent

            self._selection_accent = gallery_selection_accent()
        except Exception:
            self._selection_accent = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        try:
            from sli_ui_toolkit.widgets import OverlayScrollArea

            scroll = OverlayScrollArea(self)
        except Exception:
            from PySide6.QtWidgets import QScrollArea as _QSA

            scroll = _QSA(self)
            try:
                scroll.setWidgetResizable(True)
            except Exception:
                pass
        try:
            scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        except Exception:
            pass
        try:
            scroll.setAcceptDrops(True)
        except Exception:
            pass
        root.addWidget(scroll, 1)
        self.scroll_area = scroll

        host = QWidget(self)
        host.setObjectName("gallery_list_host")
        try:
            host.installEventFilter(self)
        except Exception:
            pass
        layout = QVBoxLayout(host)
        layout.setContentsMargins(scaled_px(8), scaled_px(8), scaled_px(8), scaled_px(8))
        layout.setSpacing(scaled_px(4))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        host.setLayout(layout)
        try:
            scroll.setWidget(host)
        except Exception:
            pass
        self.items_host = host
        self.items_layout = layout

        try:
            from sli_ui_toolkit.managers import ThemeManager

            ThemeManager.get_instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    # -- configuration -----------------------------------------------------

    def configure(self, *, on_toggle=None, on_context_menu=None) -> None:
        self._on_toggle = on_toggle
        self._on_context_menu = on_context_menu

    def _on_theme_changed(self) -> None:
        try:
            self.update()
        except Exception:
            pass
        try:
            self.apply_selection(self._selection)
        except Exception:
            pass

    # -- content -----------------------------------------------------------

    def rebuild(self, items: list[GalleryItem]) -> None:
        """Flat full rebuild (no series sections)."""
        self._items = list(items or [])
        self._series = None
        self._ungrouped = list(self._items)
        self._repaint()

    def set_series(
        self,
        series: list[list[GalleryItem]] | None,
        hub_names: list[str | None] | None = None,
        collapsed: dict[int, bool] | set[int] | list[bool] | None = None,
        mode: object = None,
    ) -> None:
        """Series sections with the exact grid semantics (grid_view parity).

        Clusters ≥2 keep sections; the rest (and empty/None series) lands
        in the UNGROUPED tail. ``collapsed`` accepts the same shapes.
        """
        _ = mode
        if not series:
            filtered: list[list[GalleryItem]] = []
        else:
            filtered = [list(s) for s in series if len(s) >= 2]
        try:
            all_items = list(self._items)
        except Exception:
            all_items = []
        if not all_items:
            all_items = [it for cl in filtered for it in cl]
        try:
            member_paths = {str(it.path) for cl in filtered for it in cl}
        except Exception:
            member_paths = set()
        self._series = filtered
        self._ungrouped = [it for it in all_items if str(it.path) not in member_paths]
        if hub_names is not None:
            try:
                self._hub_names = list(hub_names)[: len(filtered)]
                while len(self._hub_names) < len(filtered):
                    self._hub_names.append(None)
            except Exception:
                self._hub_names = [None] * len(filtered)
        else:
            self._hub_names = [None] * len(filtered)
        norm: dict[int, bool] = {}
        try:
            if isinstance(collapsed, dict):
                for k, v in collapsed.items():
                    try:
                        norm[int(k)] = bool(v)
                    except Exception:
                        continue
            elif isinstance(collapsed, set):
                for k in collapsed:
                    try:
                        norm[int(k)] = True
                    except Exception:
                        continue
            elif isinstance(collapsed, list):
                for idx, val in enumerate(collapsed):
                    if bool(val):
                        norm[idx] = True
            elif collapsed is None:
                norm = dict(getattr(self, "_collapsed", {}) or {})
                norm = {k: v for k, v in norm.items() if 0 <= k < len(filtered)}
        except Exception:
            norm = {}
        self._collapsed = norm
        self._repaint()

    def append_items(self, items: list[GalleryItem]) -> None:
        """Append-only path for pool growth (mirrors grid append fast-path).

        Fresh items land in the UNGROUPED tail (or the flat list); the next
        triage regroup rebuilds sections wholesale.
        """
        fresh = [it for it in (items or [])]
        if not fresh:
            return
        try:
            self._items = list(getattr(self, "_items", []) or []) + list(fresh)
        except Exception:
            pass
        if self._series is None:
            self._ungrouped = list(self._items)
        else:
            try:
                self._ungrouped = list(getattr(self, "_ungrouped", []) or []) + list(fresh)
            except Exception:
                pass
        self._repaint()

    def _clear_layout(self) -> None:
        while self.items_layout.count():
            try:
                ti = self.items_layout.takeAt(0)
            except Exception:
                break
            try:
                w = ti.widget()
            except Exception:
                w = None
            if w is not None:
                try:
                    w.setParent(None)
                    w.deleteLater()
                except Exception:
                    pass
        self._rows_by_path = {}

    def _make_header(self, text: str, index: int | None, collapsed: bool) -> QWidget:
        if index is None:
            lbl = Label(text, pixel_size=13, parent=self.items_host)
            lbl.setObjectName("GalleryListHeader_ungrouped")
            try:
                lbl.setBold(True)
            except Exception:
                pass
            return lbl
        arrow = "▸" if collapsed else "▾"
        display = f"{text.strip()} {arrow}"
        try:
            btn = Button(
                text=display.upper(),
                variant="ghost",
                size=(0, scaled_px(28)),
                content_align=(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                ),
                parent=self.items_host,
            )
        except Exception:
            btn = Button(text=display.upper(), variant="ghost", parent=self.items_host)
        btn.setObjectName(f"GalleryListHeaderBtn_{index}")
        try:
            btn.clicked.connect(lambda _c=False, idx=index: self._toggle_collapse(idx))
        except Exception:
            pass
        return btn

    def _repaint(self) -> None:
        self._clear_layout()
        if self._series is None:
            for it in list(self._ungrouped):
                self._add_row(it)
            return
        for idx, cluster in enumerate(list(self._series)):
            hub = self._hub_names[idx] if idx < len(self._hub_names) else None
            collapsed = bool(self._collapsed.get(idx, False))
            header = self._make_header(
                _series_header_text(idx, hub, len(cluster)), idx, collapsed
            )
            try:
                self.items_layout.addWidget(header)
            except Exception:
                pass
            if collapsed:
                continue
            for it in list(cluster):
                self._add_row(it)
        if list(self._ungrouped):
            tail = self._make_header(
                f"UNGROUPED · {len(self._ungrouped)}", None, False
            )
            try:
                self.items_layout.addWidget(tail)
            except Exception:
                pass
            for it in list(self._ungrouped):
                self._add_row(it)

    def _add_row(self, item: GalleryItem) -> None:
        try:
            row = GalleryListRow(
                item,
                parent=self.items_host,
                on_toggle=self._on_toggle,
                on_context_menu=self._on_context_menu,
            )
        except Exception:
            return
        try:
            self.items_layout.addWidget(row)
        except Exception:
            return
        try:
            self._rows_by_path[str(item.path)] = row
        except Exception:
            pass
        try:
            if str(item.path) in self._selection:
                row.set_selected(True)
        except Exception:
            pass

    def _toggle_collapse(self, index: int | None) -> None:
        if index is None:
            return
        try:
            idx = int(index)
        except Exception:
            return
        try:
            cur = dict(self._collapsed)
            cur[idx] = not cur.get(idx, False)
            self._collapsed = cur
        except Exception:
            pass
        self._repaint()

    # -- parity API --------------------------------------------------------

    def row_for(self, path: Path | str):
        try:
            return self._rows_by_path.get(str(path))
        except Exception:
            return None

    def card_for(self, path: Path | str):
        """Marquee-compat alias (marquee looks up card_for/_cards_by_path)."""
        return self.row_for(path)

    @property
    def _cards_by_path(self) -> dict:
        """Marquee-compat view over the row pool (read-only)."""
        try:
            return dict(self._rows_by_path)
        except Exception:
            return {}

    def refresh_row(self, item: GalleryItem) -> None:
        try:
            row = self._rows_by_path.get(str(item.path))
        except Exception:
            row = None
        if row is None:
            return
        try:
            row.refresh(item)
        except Exception:
            pass
        try:
            self.apply_selection(self._selection)
        except Exception:
            pass

    def refresh_rows(self, items) -> None:
        """Batch refresh with a single selection sweep (grid parity)."""
        try:
            items = list(items or [])
        except Exception:
            return
        if not items:
            return
        for item in items:
            try:
                row = self._rows_by_path.get(str(item.path))
            except Exception:
                continue
            if row is None:
                continue
            try:
                row.refresh(item)
            except Exception:
                pass
        try:
            self.apply_selection(self._selection)
        except Exception:
            pass

    def apply_selection(self, selected: set | None = None) -> None:
        if selected is None:
            selected = self._selection
        norm: set[str] = set()
        try:
            for p in selected or set():
                norm.add(str(p))
        except Exception:
            pass
        self._selection = set(norm)
        for str_path, row in list(self._rows_by_path.items()):
            try:
                row.set_selected(str_path in norm)
            except Exception:
                pass

    def items(self) -> list[GalleryItem]:
        try:
            return list(self._items)
        except Exception:
            return []

    def refresh_selection_accent(self) -> None:
        try:
            from tabs.image_gallery.ui.card.visuals import gallery_selection_accent

            self._selection_accent = gallery_selection_accent()
        except Exception:
            pass
        if self._marquee_gesture is not None:
            try:
                self._marquee_gesture.set_accent(self._selection_accent)
            except Exception:
                pass
        try:
            self.apply_selection(self._selection)
        except Exception:
            pass

    # -- eventFilter for marquee empty-area drag (grid_view parity) --------

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        try:
            from tabs.image_gallery.ui import marquee as _marquee

            if _marquee.event_filter(self, watched, event):
                return True
        except Exception:
            pass
        try:
            return super().eventFilter(watched, event)
        except Exception:
            return False
