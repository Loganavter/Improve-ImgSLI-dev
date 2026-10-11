"""A3 — Ask AI flyout surface + i18n keys (offscreen).

Covers the plan's A3 verify: default prompt present (Tab accepts it), Enter
submits, the result pane is marked "AI read", and the ask_ai i18n block exists
in all four locales.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QWidget

from tabs.image_gallery.ui.ask_ai import AskAiFlyout


def test_flyout_tab_accepts_default_and_enter_submits(qtbot):
    anchor = QWidget()
    qtbot.addWidget(anchor)
    anchor.resize(200, 100)
    anchor.show()
    qtbot.waitExposed(anchor)

    flyout = AskAiFlyout(anchor)
    qtbot.addWidget(flyout)
    got: list[str] = []
    flyout.submitted.connect(got.append)

    flyout.open_for(anchor, scope_label="Series 1", default_prompt="Summary")
    qtbot.waitUntil(lambda: flyout.isVisible(), timeout=5000)

    # Empty field: Tab accepts the grayed default prompt (our eventFilter).
    assert flyout._edit.text() == ""
    tab = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier)
    assert flyout.eventFilter(flyout._edit, tab) is True
    assert flyout._edit.text() == "Summary"

    # returnPressed sends whatever is in the field (the toolkit edit emits
    # this on Enter; the real key event is exercised live, not here — a
    # synthetic QTest Tab/Return leaves a deferred toolkit action that leaks
    # past teardown into a later theme test).
    flyout._edit.setText("custom question")
    flyout._edit.returnPressed.emit()
    assert got == ["custom question"]

    flyout.hide()


def test_flyout_submit_button_emits(qtbot):
    anchor = QWidget()
    qtbot.addWidget(anchor)
    anchor.resize(200, 100)
    anchor.show()
    qtbot.waitExposed(anchor)

    flyout = AskAiFlyout(anchor)
    qtbot.addWidget(flyout)
    got: list[str] = []
    flyout.submitted.connect(got.append)
    flyout.open_for(anchor, default_prompt="Summary")
    qtbot.waitUntil(lambda: flyout.isVisible(), timeout=5000)

    flyout._edit.setText("from button")
    flyout._submit.click()
    assert got == ["from button"]
    flyout.hide()


def test_flyout_result_is_marked_ai_read(qtbot):
    anchor = QWidget()
    qtbot.addWidget(anchor)
    anchor.resize(200, 100)
    anchor.show()
    qtbot.waitExposed(anchor)

    flyout = AskAiFlyout(anchor)
    qtbot.addWidget(flyout)
    flyout.open_for(anchor, default_prompt="Summary")
    qtbot.waitUntil(lambda: flyout.isVisible(), timeout=5000)

    flyout.show_result("The series is mostly clean.", backend="text")
    assert "AI read" in flyout._status.text()
    assert "clean" in flyout._result.text()

    flyout.show_error("Configure the AI API key in Settings first.")
    assert "Configure" in flyout._status.text()
    flyout.hide()


def test_series_header_context_callback_passes_members_and_label(qtbot):
    from tabs.image_gallery.models import GalleryItem
    from tabs.image_gallery.ui.grid_view import GalleryGridView

    grid = GalleryGridView()
    qtbot.addWidget(grid)
    calls = []
    grid._on_series_context_menu = lambda idx, anchor, paths, label: calls.append(
        (idx, tuple(paths), label)
    )
    item = GalleryItem(path=Path("/g/1.png"), mtime_ns=1)
    grid._series = [[item]]
    grid._series_header_labels = {0: "Series One"}
    anchor = QWidget()
    qtbot.addWidget(anchor)

    grid._handle_series_context(anchor, 0)

    assert calls == [(0, (item.path,), "Series One")]


def test_i18n_ask_ai_keys_present_in_all_locales():
    base = Path(__file__).resolve().parents[1] / "resources" / "i18n"
    files = sorted(base.glob("*/image_gallery.json"))
    assert len(files) == 4
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        block = data["image_gallery"]["ask_ai"]
        for key in (
            "action",
            "title",
            "default_prompt",
            "read_badge",
            "error",
            "routing_unavailable",
        ):
            assert block.get(key), f"{path}: missing ask_ai.{key}"
