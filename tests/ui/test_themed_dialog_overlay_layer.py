"""In-window flyouts opened from a child of a ``ThemedDialog`` must not clip.

Regression (task-in-window-flyout-clipping-2026-10-21): ``ThemedDialog`` — the
base of every app dialog — owned no ``OverlayLayer``. ``surface="in_window"``
menus are plain child widgets, so the toolkit resolver found no overlay host
and left the ``ContextMenu`` parented to its small source widget; Qt clips
child widgets to their parent's rect, so the menu painted as a sliver
(measured: 32x26 of 131x141). ``MainWindow`` and ``HelpDialog`` had their own
layer; every other dialog did not.

The negative control runs the *same* probe on a bare ``QDialog`` and pins the
clipped parent: the layer (not the dialog class name) is the mechanism.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from shared_toolkit.ui.overlay_layer import OverlayLayer, get_overlay_layer
from shared_toolkit.ui.themed_dialog import ThemedDialog
from sli_ui_toolkit.config import configure_toolkit, reset_toolkit_config
from sli_ui_toolkit.widgets import (
    Button,
    ContextMenuAction,
    ContextMenuSeparator,
)
from ui.context_menu.manager import (
    get_context_menu_manager,
    open_context_menu_entries,
    rmb_context_menu_surface,
)

_ENTRIES = (
    ContextMenuAction("open", "Open", shortcut="Ctrl+O", enabled=True),
    ContextMenuAction("rename", "Rename", shortcut="F2", enabled=True),
    ContextMenuSeparator(),
    ContextMenuAction("remove", "Remove", shortcut="Del", enabled=True),
)


@pytest.fixture
def _overlay_resolver():
    """Mirror the app: ``configure_toolkit`` wires the app overlay resolver.

    conftest resets the toolkit config per test, so this must be re-armed;
    without a resolver no flyout/menu ever re-parents to a host layer.
    """
    configure_toolkit(overlay_resolver=get_overlay_layer)
    try:
        yield
    finally:
        reset_toolkit_config()


class _ProbeDialog(ThemedDialog):
    """Minimal app-dialog stand-in (the base is what the fix touches)."""


def _dialog_with_small_child(host):
    """A small Button near the bottom edge of ``host`` (children clip).

    Deliberately no ``show()``/``waitExposed``: in-window parenting and the
    geometry containment below are decided without a window activation, and
    activating a window here trips a pre-existing suite-level stale-receiver
    segfault (``QApplicationPrivate::setActiveWindow`` -> PySide
    ``getWrapperForQObject`` on a QObject an earlier test already freed; see
    tests/conftest.py ``_destroy_lingering_toplevels``).
    """
    host.resize(640, 420)
    layout = QVBoxLayout(host)
    layout.addStretch(1)
    button = Button("Header")
    button.setFixedHeight(30)
    layout.addWidget(button)
    return button


def _open_menu_on(button, key):
    assert rmb_context_menu_surface() == "in_window", (
        "this regression is about in_window (child-widget) menus; a popup "
        "surface is a top-level and cannot clip"
    )
    pos = button.mapToGlobal(QPoint(button.width(), button.height()))
    return open_context_menu_entries(
        source_widget=button,
        global_pos=pos,
        entries=_ENTRIES,
        key=("themed-dialog-layer", key),
        on_triggered=lambda *_args: None,
    )


@pytest.fixture
def _closed_menu():
    yield
    get_context_menu_manager().hide_active_menu()


def test_themed_dialog_hosts_in_window_menu(
    qtbot, _overlay_resolver, _closed_menu
):
    """A menu opened from a child of ``ThemedDialog`` is hosted, not clipped."""
    dialog = _ProbeDialog()
    qtbot.addWidget(dialog)
    button = _dialog_with_small_child(dialog)

    # The dialog base is its own window and must own its overlay host.
    assert get_overlay_layer(button) is dialog.overlay_layer

    menu = _open_menu_on(button, "themed")
    assert menu is not None, "menu did not open (probe is vacuous)"

    parent = menu.parentWidget()
    assert parent is dialog, (
        f"in-window menu parented to {type(parent).__name__}, expected the "
        "dialog's overlay host"
    )
    # Non-vacuity: the menu is taller than its anchor, so clipping it to the
    # child would have been visible (that was the bug).
    assert menu.height() > button.height()
    visible = QRect(menu.geometry()).intersected(dialog.rect())
    assert visible == QRect(menu.geometry()), (
        f"menu {QRect(menu.geometry()).getRect()} is clipped by the dialog "
        f"rect {dialog.rect().getRect()} -> visible {visible.getRect()}"
    )


def test_bare_dialog_still_clips_negative_control(
    qtbot, _overlay_resolver, _closed_menu
):
    """Same probe on a plain ``QDialog`` stays parented to the small child.

    Proves the overlay layer is the mechanism, not the dialog class name.
    """
    dialog = QDialog()
    qtbot.addWidget(dialog)
    button = _dialog_with_small_child(dialog)

    assert get_overlay_layer(button) is None

    menu = _open_menu_on(button, "bare")
    assert menu is not None

    parent = menu.parentWidget()
    assert parent is button, (
        "without an overlay host the menu must stay on its source widget"
    )
    assert menu.height() > button.height()
    visible = QRect(menu.geometry()).intersected(button.rect())
    assert visible != QRect(menu.geometry()), (
        "negative control is no longer clipped — the probe stopped "
        "reproducing the bug it guards"
    )


def test_help_dialog_has_exactly_one_overlay_layer(qtbot):
    """HelpDialog must not stack a second layer on the base's one."""
    from plugins.help.dialog import HelpDialog

    dialog = HelpDialog("en", "Improve-ImgSLI")
    qtbot.addWidget(dialog)

    layers = [c for c in dialog.children() if isinstance(c, OverlayLayer)]
    assert len(layers) == 1, f"expected one overlay layer, found {len(layers)}"
    assert layers[0] is dialog.overlay_layer


def test_help_dialog_source_creates_no_overlay_layer():
    """Source-level dedupe guard (no app context needed).

    The base owns the layer; a second ``OverlayLayer(...)`` in the HelpDialog
    body would give the dialog two hosts and split flyout re-parenting.
    """
    source = (
        Path(__file__).resolve().parents[2] / "src" / "plugins" / "help" / "dialog.py"
    ).read_text(encoding="utf-8")
    assert "OverlayLayer(" not in source


def test_every_app_dialog_inherits_themed_dialog():
    """Blast-radius guard: the fix lands through the shared base, not per dialog.

    Only ``HelpDialog`` is constructed in this module (the other nine need app
    context), but all of them inherit the same base class — the layer is not a
    per-dialog override.
    """
    from plugins.diagnostics.dialog import DiagnosticsDialog
    from plugins.export.dialog import ExportDialog
    from plugins.help.dialog import HelpDialog
    from plugins.image_properties.dialog import ImagePropertiesDialog
    from plugins.settings.dialog import SettingsDialog
    from shared_toolkit.ui.message_dialog import AppMessageDialog
    from shared_toolkit.ui.text_input_dialog import AppTextInputDialog
    from tabs.image_compare.plugins.video_editor.dialog.shell import (
        VideoEditorDialog,
    )
    from ui.actions.palette.dialog import FindActionDialog
    from ui.widgets.color.picker_dialog import ColorPickerDialog

    dialogs = (
        ExportDialog,
        SettingsDialog,
        ImagePropertiesDialog,
        VideoEditorDialog,
        DiagnosticsDialog,
        AppTextInputDialog,
        AppMessageDialog,
        ColorPickerDialog,
        FindActionDialog,
        HelpDialog,
    )
    assert len(dialogs) == 10
    for cls in dialogs:
        assert issubclass(cls, ThemedDialog), f"{cls.__name__} bypasses the base"


def test_overlay_layer_owns_no_widget_and_eats_no_clicks(qtbot, _overlay_resolver):
    """The layer is a controller, not a surface: it must not intercept input.

    ``OverlayLayer`` is a ``QObject`` that re-parents flyouts onto the dialog; it
    owns no pixels, so a click on a control under it must reach the control.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    dialog = _ProbeDialog()
    qtbot.addWidget(dialog)
    button = _dialog_with_small_child(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)

    layer = dialog.overlay_layer
    assert not isinstance(layer, QWidget), type(layer).__name__
    assert layer.host is dialog

    # hit-testing (what the platform routes a real click through)
    from PySide6.QtWidgets import QApplication

    centre = button.mapToGlobal(button.rect().center())
    assert QApplication.widgetAt(centre) is button, "something covers the control"

    clicked: list[int] = []
    button.clicked.connect(lambda *_: clicked.append(1))
    QTest.mouseClick(button, Qt.MouseButton.LeftButton, pos=button.rect().center())
    assert clicked, "the click never reached the control under the layer"


def test_dialog_parented_to_layered_window_uses_its_own_layer(
    qtbot, _overlay_resolver, _closed_menu
):
    """No main-window fallback: a parented dialog resolves ITS OWN host.

    App dialogs are usually constructed with the main window as parent; before
    the fix the resolver walked past the dialog to the main window's layer (and
    the toolkit's same-window guard then rejected it, leaving the menu clipped).
    """
    parent_window = ThemedDialog()
    qtbot.addWidget(parent_window)
    parent_window.resize(900, 600)
    parent_window.show()
    qtbot.waitExposed(parent_window)

    dialog = _ProbeDialog(parent_window)
    qtbot.addWidget(dialog)
    button = _dialog_with_small_child(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)

    assert dialog.overlay_layer is not parent_window.overlay_layer
    assert get_overlay_layer(button) is dialog.overlay_layer

    menu = _open_menu_on(button, "parented")
    assert menu is not None
    assert menu.parentWidget() is dialog, (
        "a parented dialog must host its own menu, not the main window's"
    )
