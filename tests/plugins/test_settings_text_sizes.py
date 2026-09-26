"""Settings dialog typography groups (TITLE / BODY / CAPTION).

Regression: settings pages must size text through
``plugins.settings.typography`` instead of hardcoded ``pixel_size=``
literals, so the whole dialog scales as one system:

- TITLE (18px) — every ``CustomGroupWidget`` caption;
- BODY (16px) — checkboxes, radios, combos, edits, spins, primary labels;
- CAPTION (14px) — hints, warnings, footnotes.

Toolkit-owned chrome (sidebar rows, search fields, ``Button`` family) is
out of scope and keeps its own sizing.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from plugins.settings.dialog import SettingsDialog
from plugins.settings.typography import (
    SETTINGS_BODY_PX,
    SETTINGS_CAPTION_PX,
    SETTINGS_TITLE_PX,
)
from sli_ui_toolkit.managers import UiScale
from sli_ui_toolkit.widgets import (
    CheckBox,
    ComboBox,
    CustomGroupWidget,
    CustomLineEdit,
    Label,
)


@pytest.fixture(autouse=True)
def _scale_one():
    UiScale.get_instance().set_factor(1.0)
    yield
    UiScale.get_instance().set_factor(1.0)


def _dialog(qapp: QApplication) -> SettingsDialog:
    dialog = SettingsDialog("en", "dark", 60, 10, 200, False, True)
    dialog.show()
    qapp.processEvents()
    return dialog


def _px(widget: QWidget) -> int:
    return widget.font().pixelSize()


def test_typography_ladder_ordering():
    assert SETTINGS_TITLE_PX > SETTINGS_BODY_PX > SETTINGS_CAPTION_PX
    assert (SETTINGS_TITLE_PX, SETTINGS_BODY_PX, SETTINGS_CAPTION_PX) == (18, 16, 14)


def test_settings_group_titles_are_title(qapp: QApplication):
    dialog = _dialog(qapp)
    try:
        groups = dialog.findChildren(CustomGroupWidget)
        assert groups, "settings dialog must build group widgets"
        for group in groups:
            assert _px(group) == SETTINGS_TITLE_PX, group.get_title()
            # Flush sides: rows align to the group edge, no group-level
            # horizontal insets (vertical title clearance untouched).
            margins = group.layout().contentsMargins()
            assert margins.left() == 0, group.get_title()
            assert margins.right() == 0, group.get_title()
    finally:
        dialog.close()


def test_settings_checkboxes_are_body(qapp: QApplication):
    dialog = _dialog(qapp)
    try:
        for box in (
            dialog.system_notifications_checkbox,
            dialog.debug_checkbox,
            dialog.crop_checkbox,
            dialog.auto_psnr_checkbox,
            dialog.auto_ssim_checkbox,
            dialog.optimize_movement_checkbox,
            dialog.laser_smoothing_checkbox,
            dialog.magnifier_intersection_highlight_checkbox,
            dialog.magnifier_auto_color_checkbox,
        ):
            assert isinstance(box, CheckBox)
            assert _px(box) == SETTINGS_BODY_PX, box.text()
    finally:
        dialog.close()


def test_settings_radios_combos_spins_are_body(qapp: QApplication):
    dialog = _dialog(qapp)
    try:
        radios = (
            dialog.radio_en,
            dialog.radio_ru,
            dialog.radio_zh,
            dialog.radio_pt_br,
            dialog.radio_ui_mode_beginner,
            dialog.radio_ui_mode_advanced,
            dialog.radio_ui_mode_expert,
            dialog.radio_font_builtin,
            dialog.radio_font_system_default,
            dialog.radio_font_system_custom,
        )
        assert radios
        for rb in radios:
            assert _px(rb) == SETTINGS_BODY_PX, rb.text()
        for combo in (
            dialog.combo_theme,
            dialog.combo_font_family,
            dialog.combo_rhi_backend,
            dialog.combo_zoom_interp,
            dialog.combo_mag_interp,
            dialog.combo_laser_interp,
        ):
            assert isinstance(combo, ComboBox)
            assert _px(combo) == SETTINGS_BODY_PX
        assert _px(dialog.spin_max_length) == SETTINGS_BODY_PX
    finally:
        dialog.close()


def test_settings_primary_labels_are_body(qapp: QApplication):
    dialog = _dialog(qapp)
    try:
        assert dialog._keyboard_action_labels
        for name, _key in dialog._keyboard_action_labels:
            assert _px(name) == SETTINGS_BODY_PX, name.text()
    finally:
        dialog.close()


def test_settings_gallery_ai_page_is_body(qapp: QApplication):
    dialog = _dialog(qapp)
    try:
        assert isinstance(dialog.gallery_ai_enabled, CheckBox)
        assert _px(dialog.gallery_ai_enabled) == SETTINGS_BODY_PX
        for field in (
            dialog.gallery_ai_base_url,
            dialog.gallery_ai_api_key,
            dialog.gallery_ai_model,
        ):
            assert isinstance(field, CustomLineEdit)
            assert _px(field) == SETTINGS_BODY_PX, field.placeholderText()
        # password echo + placeholder survive the typography pass
        assert dialog.gallery_ai_api_key.placeholderText()
        from PySide6.QtWidgets import QLineEdit

        assert dialog.gallery_ai_api_key.echoMode() == QLineEdit.EchoMode.Password
    finally:
        dialog.close()


def test_settings_perf_extras_are_body(qapp: QApplication):
    dialog = _dialog(qapp)
    try:
        assert isinstance(dialog.lbl_zoom_interp, Label)
        assert _px(dialog.lbl_zoom_interp) == SETTINGS_BODY_PX
        assert isinstance(dialog.lbl_fps, Label)
        assert _px(dialog.lbl_fps) == SETTINGS_BODY_PX
        assert dialog.lbl_fps.text() == "FPS:"
        assert _px(dialog.spin_fps) == SETTINGS_BODY_PX
        dialog.spin_fps.setValue(60)
        assert dialog.spin_fps.value() == 60
    finally:
        dialog.close()


def test_settings_gallery_labels_fit(qapp: QApplication):
    """Gallery AI row labels are wide enough for their text (BODY size).

    Regression: at 110px the Cyrillic labels clipped under the line edit.
    """
    from PySide6.QtGui import QFontMetrics

    dialog = _dialog(qapp)
    try:
        for label in (
            dialog.gallery_ai_base_url_label,
            dialog.gallery_ai_api_key_label,
            dialog.gallery_ai_model_label,
        ):
            need = QFontMetrics(label.font()).horizontalAdvance(label.text())
            assert label.width() >= need, (label.text(), label.width(), need)
    finally:
        dialog.close()


def test_settings_captions_are_caption(qapp: QApplication):
    """Secondary text (hints/warnings) uses CAPTION, shell chrome stays smaller."""
    dialog = _dialog(qapp)
    try:
        assert _px(dialog.lbl_rhi_backend_hint) == SETTINGS_CAPTION_PX
        for field in (dialog.search_field, dialog._keyboard_search):
            assert isinstance(field, CustomLineEdit)
            assert field.placeholderText(), "search field must keep its hint"
            assert _px(field) < SETTINGS_BODY_PX
    finally:
        dialog.close()
