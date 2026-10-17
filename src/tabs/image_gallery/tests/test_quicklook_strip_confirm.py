"""Quick Look strip cursor: arrows select, Enter confirms (nav_section.py).

Behaviour contract changed in the 2026-10-17 session: ``←``/``→`` (and the
``‹``/``›`` circles) used to re-bind the preview on every press. Now they move a
**cursor** along the filmstrip and the picture follows only on ``Enter`` (or a
thumb click, where the mouse has already named its target).

Falsification (written to be RED against the previous behaviour and against a
naive "always populate" commit):

* ``test_arrows_move_the_cursor_without_rebinding`` fails if an arrow calls
  ``_walk`` — the recorded populate count must be 0 and ``_current_idx``
  unchanged while the cursor advances and the thumb takes focus;
* ``test_commit_is_a_no_op_when_the_cursor_is_already_current`` fails if the
  commit populates unconditionally;
* ``test_cursor_wraps`` fails a clamped (non-wrapping) cursor;
* ``test_section_claims_overlay_subtree_only`` fails an ``owns`` that claims the
  whole window (arrows would never leave the panel);
* ``test_extra_keys_claim_enter_but_not_escape`` fails if Escape is claimed
  (the overlay's own close path must stay as it is).

Runs offscreen (no Xvfb) over a stub overlay: the real ``QuickLookOverlay``
needs a controller and a decoded series, neither of which any of these
assertions depend on.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from sli_ui_toolkit.widgets import Button

from tabs.image_gallery.ui.quick_look import nav_section as nav
from tabs.image_gallery.ui.quick_look.overlay_parts import populate as populate_parts


class _StubOverlay(QWidget):
    """A QWidget carrying exactly the attributes nav_section reads."""

    def __init__(self, parent: QWidget, n: int = 4) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self._series_items = [f"item{i}" for i in range(n)]
        self._current_idx = 0
        self._current_item = self._series_items[0]
        self._strip_buttons = [Button(text=f"t{i}", parent=self) for i in range(n)]
        for button in self._strip_buttons:
            layout.addWidget(button)
        self._set_source_btn = Button(text="Set as source", parent=self)
        self._reject_btn = Button(text="Reject", parent=self)
        self._delete_btn = Button(text="Delete", parent=self)
        for button in (self._set_source_btn, self._reject_btn, self._delete_btn):
            layout.addWidget(button)
        self.populates: list[bool] = []

    def _populate(self, preserve_view: bool = False) -> None:  # noqa: N802 (Qt-ish name)
        self.populates.append(bool(preserve_view))


def _qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _patch_populate(monkeypatch, overlay: _StubOverlay) -> list[bool]:
    """Record re-binds at the module seam commit/walk actually call."""
    calls: list[bool] = []

    def _recorder(ov, preserve_view: bool = False) -> None:  # noqa: ANN001
        calls.append(bool(preserve_view))
        ov.populates.append(bool(preserve_view))

    monkeypatch.setattr(populate_parts, "_populate", _recorder, raising=False)
    return calls


def _overlay(qtbot) -> tuple[_StubOverlay, QWidget]:
    parent = QWidget()
    qtbot.addWidget(parent)
    parent.resize(420, 320)
    overlay = _StubOverlay(parent)
    parent.show()
    overlay.show()
    QApplication.processEvents()
    return overlay, parent


def test_arrows_move_the_cursor_without_rebinding(qtbot, monkeypatch) -> None:
    overlay, _parent = _overlay(qtbot)
    binds = _patch_populate(monkeypatch, overlay)
    nav.sync_cursor_to_current(overlay)
    assert binds == [], "sync must not re-bind the preview"

    nav.move_cursor(overlay, 1)
    assert nav.cursor_index(overlay) == 1
    assert overlay._current_idx == 0, "the picture must not follow the arrow"
    assert binds == [], "an arrow must not re-populate"
    assert QApplication.focusWidget() is overlay._strip_buttons[1], (
        "the cursor must be visible: the thumb takes keyboard focus"
    )

    nav.move_cursor(overlay, 1)
    assert nav.cursor_index(overlay) == 2
    assert binds == []
    assert overlay._current_idx == 0


def test_enter_commits_the_cursor_and_rebinds_once(qtbot, monkeypatch) -> None:
    overlay, _parent = _overlay(qtbot)
    binds = _patch_populate(monkeypatch, overlay)
    nav.sync_cursor_to_current(overlay)
    nav.move_cursor(overlay, 2)

    assert nav.commit_cursor(overlay) is True
    assert overlay._current_idx == 2, "Enter must land the picture on the cursor"
    assert binds == [True], "exactly one re-bind, view preserved"
    assert nav.cursor_index(overlay) == 2


def test_commit_is_a_no_op_when_the_cursor_is_already_current(qtbot, monkeypatch) -> None:
    overlay, _parent = _overlay(qtbot)
    binds = _patch_populate(monkeypatch, overlay)
    nav.sync_cursor_to_current(overlay)

    assert nav.commit_cursor(overlay) is False
    assert binds == [], "confirming the shown item must not re-decode"


def test_cursor_wraps(qtbot) -> None:
    overlay, _parent = _overlay(qtbot)
    nav.sync_cursor_to_current(overlay)  # cursor 0 of 4
    nav.move_cursor(overlay, -1)
    assert nav.cursor_index(overlay) == 3, "the cursor wraps like the walk did"
    nav.move_cursor(overlay, 1)
    assert nav.cursor_index(overlay) == 0


def test_down_reaches_the_action_row_and_up_returns(qtbot) -> None:
    overlay, _parent = _overlay(qtbot)
    nav.sync_cursor_to_current(overlay)

    assert nav.focus_action_row(overlay) is True
    assert QApplication.focusWidget() is overlay._set_source_btn, (
        "↓ must hand the cursor to the first action-row control"
    )
    assert nav.zone_of(overlay) == "actions"
    assert nav.focus_strip(overlay) is True
    assert QApplication.focusWidget() is overlay._strip_buttons[0], (
        "↑ must bring the cursor back to the strip"
    )
    assert nav.zone_of(overlay) == "strip"


def test_action_row_is_three_buttons_and_walks_between_them(qtbot) -> None:
    """The row holds Set as source / Reject / Delete — the cursor walks all three.

    Falsification for the 2026-10-17 report: a ↓ that only ever lands on the
    first button leaves Reject and Delete unreachable by keyboard.
    """
    overlay, _parent = _overlay(qtbot)
    row = nav.action_row_buttons(overlay)
    assert row == [overlay._set_source_btn, overlay._reject_btn, overlay._delete_btn]
    nav.focus_action_row(overlay)
    assert QApplication.focusWidget() is overlay._set_source_btn

    nav.move_action_cursor(overlay, 1)
    assert QApplication.focusWidget() is overlay._reject_btn, "→ must reach Reject"
    assert nav.action_index(overlay) == 1
    nav.move_action_cursor(overlay, 1)
    assert QApplication.focusWidget() is overlay._delete_btn, "→ must reach Delete"
    assert nav.action_index(overlay) == 2

    nav.move_action_cursor(overlay, 1)  # clamped, not a carousel
    assert nav.action_index(overlay) == 2
    nav.move_action_cursor(overlay, -1)
    assert QApplication.focusWidget() is overlay._reject_btn
    assert nav.action_index(overlay) == 1


def test_enter_in_the_action_row_activates_that_button(qtbot, monkeypatch) -> None:
    """Enter on a row button presses *that* button, never the strip confirm."""
    overlay, _parent = _overlay(qtbot)
    binds = _patch_populate(monkeypatch, overlay)
    nav.sync_cursor_to_current(overlay)
    pressed: list[str] = []
    for button, name in (
        (overlay._set_source_btn, "source"),
        (overlay._reject_btn, "reject"),
        (overlay._delete_btn, "delete"),
    ):
        button.clicked.connect(lambda _checked=False, n=name: pressed.append(n))

    section = nav.QuickLookNavSection(overlay)
    assert section.navigate(Qt.Key.Key_Down, overlay) is True
    assert section.navigate(Qt.Key.Key_Right, overlay) is True
    assert QApplication.focusWidget() is overlay._reject_btn
    assert section.navigate(Qt.Key.Key_Return, overlay) is True
    assert pressed == ["reject"], pressed
    assert binds == [], "the strip must not be confirmed from the action row"

    nav.move_action_cursor(overlay, 1)
    section.navigate(Qt.Key.Key_Return, overlay)
    assert pressed == ["reject", "delete"], pressed

    assert section.navigate(Qt.Key.Key_Up, overlay) is True
    assert nav.zone_of(overlay) == "strip"
    assert section.navigate(Qt.Key.Key_Right, overlay) is True
    assert section.navigate(Qt.Key.Key_Return, overlay) is True
    assert binds == [True], "Enter back in the strip confirms the cursor"
    assert pressed == ["reject", "delete"], "no stray button activation"


def test_walk_keeps_the_cursor_with_the_shown_picture(qtbot) -> None:
    """A confirmed switch (thumb click / ‹›) moves the cursor too."""
    overlay, _parent = _overlay(qtbot)
    nav.sync_cursor_to_current(overlay)
    overlay._current_idx = 2  # what a thumb click does
    nav.sync_cursor_to_current(overlay)
    assert nav.cursor_index(overlay) == 2


def test_section_claims_overlay_subtree_only(qtbot) -> None:
    overlay, parent = _overlay(qtbot)
    section = nav.QuickLookNavSection(overlay)

    assert section.owns(overlay) is True
    assert section.owns(overlay._strip_buttons[0]) is True
    assert section.owns(parent) is False, "arrows behind the panel are not ours"
    assert section.owns(None) is False


def test_section_navigates_cursor_and_enter(qtbot, monkeypatch) -> None:
    overlay, _parent = _overlay(qtbot)
    binds = _patch_populate(monkeypatch, overlay)
    nav.sync_cursor_to_current(overlay)
    section = nav.QuickLookNavSection(overlay)

    assert section.navigate(Qt.Key.Key_Right, overlay) is True
    assert nav.cursor_index(overlay) == 1
    assert binds == [], "section arrows must not re-bind"
    assert section.navigate(Qt.Key.Key_Return, overlay) is True
    assert overlay._current_idx == 1
    assert binds == [True]
    assert section.navigate(Qt.Key.Key_Left, overlay) is True
    assert section.navigate(Qt.Key.Key_Down, overlay) is True
    assert nav.zone_of(overlay) == "actions"
    assert section.navigate(Qt.Key.Key_Up, overlay) is True
    assert nav.zone_of(overlay) == "strip"
    assert section.navigate(Qt.Key.Key_Escape, overlay) is False, (
        "Escape keeps the overlay's own close path"
    )


def test_extra_keys_claim_enter_but_not_escape(qtbot) -> None:
    overlay, _parent = _overlay(qtbot)
    keys = nav.QuickLookNavSection(overlay).extra_keys  # a property, not a call
    assert Qt.Key.Key_Return in keys and Qt.Key.Key_Enter in keys
    assert Qt.Key.Key_Left in keys and Qt.Key.Key_Right in keys, (
        "horizontal arrows must be claimed, or the manager yields them to "
        "native delivery and the section never moves the cursor"
    )
    assert Qt.Key.Key_Escape not in keys


def test_extra_keys_survive_the_managers_raw_read(qtbot) -> None:
    """The falsification for the live crash of 2026-10-17.

    ``NavigationManager.eventFilter`` (and ``nav_graph``) iterate the *raw*
    attribute — ``key in getattr(spec, "extra_keys", frozenset())`` — so a
    method-shaped declaration raised
    ``TypeError: argument of type 'method' is not a container or iterable`` on
    every ←/→ while the overlay owned focus, killing section routing (and the
    app's diagnostics dialog reported it). Pinned against the manager's own
    expression, not against my reading of it.
    """
    overlay, _parent = _overlay(qtbot)
    spec = nav.QuickLookNavSection(overlay)
    assert isinstance(type(spec).extra_keys, property), (
        "extra_keys must be a property: readers iterate it raw"
    )
    raw = getattr(spec, "extra_keys", frozenset())  # the manager's exact read
    assert isinstance(raw, frozenset), f"raw read must be iterable, got {type(raw)}"
    assert {Qt.Key.Key_Return, Qt.Key.Key_Enter} <= raw
    for key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Return):
        assert (key in raw) in (True, False), key


def test_focus_first_lands_on_the_shown_item_not_the_first(qtbot) -> None:
    """The panel's "first" item is the one on screen — no wandering ring."""
    overlay, _parent = _overlay(qtbot)
    overlay._current_idx = 3
    section = nav.QuickLookNavSection(overlay)
    assert section.focus_first(reason=Qt.FocusReason.OtherFocusReason) is True
    assert nav.cursor_index(overlay) == 3
    assert QApplication.focusWidget() is overlay._strip_buttons[3]
    assert section.focus_last(reason=Qt.FocusReason.OtherFocusReason) is True
    assert nav.cursor_index(overlay) == 3
