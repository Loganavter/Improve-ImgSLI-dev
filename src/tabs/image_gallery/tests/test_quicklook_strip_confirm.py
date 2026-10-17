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
        # Mirrors the real strip: ``_strip_buttons`` holds CONTAINERS, each with
        # the thumb Button named ``quicklook_strip_N`` inside it — focusing a
        # container paints no ring, which is exactly how the cursor went
        # invisible live (2026-10-17).
        self._strip_buttons = []
        self._thumb_buttons = []
        for i in range(n):
            container = QWidget(self)
            container.setObjectName(f"quicklook_strip_container_{i}")
            inner = QVBoxLayout(container)
            button = Button(text=f"t{i}", parent=container)
            button.setObjectName(f"quicklook_strip_{i}")
            inner.addWidget(button)
            layout.addWidget(container)
            self._strip_buttons.append(container)
            self._thumb_buttons.append(button)
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
    assert QApplication.focusWidget() is overlay._thumb_buttons[1], (
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
    assert QApplication.focusWidget() is overlay._thumb_buttons[0], (
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
    assert section.owns(overlay._thumb_buttons[0]) is True
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
    assert QApplication.focusWidget() is overlay._thumb_buttons[3]
    assert section.focus_last(reason=Qt.FocusReason.OtherFocusReason) is True
    assert nav.cursor_index(overlay) == 3

def test_cursor_focuses_the_thumb_button_not_its_container(qtbot) -> None:
    """Falsification for the live report "no indication while navigating".

    ``_strip_buttons`` holds containers; focusing one paints no ring (the toolkit
    ring lives on the ``Button``), so the cursor was invisible.
    """
    overlay, _parent = _overlay(qtbot)
    nav.sync_cursor_to_current(overlay)
    nav.move_cursor(overlay, 2)
    focused = QApplication.focusWidget()
    assert focused is overlay._thumb_buttons[2], f"focused {type(focused).__name__}"
    assert focused is not overlay._strip_buttons[2]
    assert nav.thumb_widget(overlay, 2) is overlay._thumb_buttons[2]


def test_cursor_marker_is_painted_on_exactly_one_thumb(qtbot) -> None:
    """The cursor has its own marker — it must not depend on Qt focus."""
    overlay, _parent = _overlay(qtbot)
    nav.sync_cursor_to_current(overlay)
    nav.move_cursor(overlay, 1)
    flags = [bool(b.property("strip_cursor")) for b in overlay._thumb_buttons]
    assert flags == [False, True, False, False], flags


def test_cursor_survives_a_strip_rebuild(qtbot) -> None:
    """After a confirmed step the strip is rebuilt: the cursor must re-apply.

    Live report #1 ("navigation dies after Enter"): the focused thumb widget is
    replaced by the rebuild, so focus — and with it the section routing — was
    lost. ``reapply_cursor`` re-asserts both on the live widgets.
    """
    overlay, _parent = _overlay(qtbot)
    nav.sync_cursor_to_current(overlay)
    nav.move_cursor(overlay, 2)

    # A rebuild: fresh containers, fresh buttons (same order).
    fresh_containers, fresh_thumbs = [], []
    for i in range(len(overlay._series_items)):
        container = QWidget(overlay)
        container.setObjectName(f"quicklook_strip_container_{i}")
        lay = QVBoxLayout(container)
        button = Button(text=f"t{i}", parent=container)
        button.setObjectName(f"quicklook_strip_{i}")
        lay.addWidget(button)
        fresh_containers.append(container)
        fresh_thumbs.append(button)
    overlay._strip_buttons = fresh_containers
    overlay._thumb_buttons = fresh_thumbs

    nav.reapply_cursor(overlay)
    QApplication.processEvents()
    assert nav.cursor_index(overlay) == 2, "the index survives the rebuild"
    assert bool(fresh_thumbs[2].property("strip_cursor")) is True
    assert QApplication.focusWidget() is fresh_thumbs[2], (
        "focus must land on the live thumb, or section routing dies"
    )


def test_reapply_does_not_steal_focus_from_the_action_row(qtbot) -> None:
    """A background repopulate must not yank the user off a button."""
    overlay, _parent = _overlay(qtbot)
    nav.sync_cursor_to_current(overlay)
    section = nav.QuickLookNavSection(overlay)
    section.navigate(Qt.Key.Key_Down, overlay)  # into the action row
    section.navigate(Qt.Key.Key_Right, overlay)
    assert QApplication.focusWidget() is overlay._reject_btn

    nav.reapply_cursor(overlay)
    QApplication.processEvents()
    assert QApplication.focusWidget() is overlay._reject_btn, (
        "the cursor re-apply must leave the action row alone"
    )

def test_zone_survives_focus_moving_out_of_the_panel(qtbot) -> None:
    """Zone falsification: the live chain re-anchors focus outside the panel.

    The control channel focuses the canvas before every injected key, and a
    background repopulate can move focus too. With the zone read from focus
    alone, → after ↓ walked the filmstrip instead of the three buttons
    (measured live 2026-10-17); the remembered zone is what makes the row work.
    """
    overlay, _parent = _overlay(qtbot)
    nav.sync_cursor_to_current(overlay)
    section = nav.QuickLookNavSection(overlay)
    assert section.navigate(Qt.Key.Key_Down, overlay) is True
    assert nav.zone_of(overlay) == "actions"

    # Something outside the panel takes focus (canvas / window / driver).
    overlay.setFocus(Qt.FocusReason.OtherFocusReason)
    QApplication.processEvents()
    assert nav.zone_of(overlay) == "actions", "the remembered zone must answer"

    assert section.navigate(Qt.Key.Key_Right, overlay) is True
    assert QApplication.focusWidget() is overlay._reject_btn, (
        "→ must walk the action row, not the filmstrip"
    )
    assert nav.cursor_index(overlay) == 0, "the strip cursor must not move"
    assert section.navigate(Qt.Key.Key_Up, overlay) is True
    assert nav.zone_of(overlay) == "strip"
    assert QApplication.focusWidget() is overlay._thumb_buttons[0]
