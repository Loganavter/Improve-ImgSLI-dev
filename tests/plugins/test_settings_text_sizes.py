"""Settings dialog primary-text sizes (readability sweep).

Regression: the settings dialog rendered primary text at the 11pt app font
(CheckBox/Radio/Combo/Spin) / 12px Label defaults while the rest of the app
moved to a 14px body. Every primary control built by the in-scope settings
pages must resolve to 14px at UiScale 1.0; hints, placeholders and secondary
captions stay at 11-12px.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from plugins.settings.dialog import SettingsDialog
from sli_ui_toolkit.managers import UiScale
from sli_ui_toolkit.widgets import CheckBox, ComboBox, CustomLineEdit, Label


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


def test_settings_checkboxes_are_14px(qapp: QApplication):
    dialog = _dialog(qapp)
    try:
        for box in (
            dialog.system_notifications_checkbox,
            dialog.debug_checkbox,
            dialog.crop_checkbox,
            dialog.auto_psnr_checkbox,
            dialog.auto_ssim_checkbox,
        ):
            assert isinstance(box, CheckBox)
            assert _px(box) == 14, box.text()
    finally:
        dialog.close()


def test_settings_radios_and_combos_are_14px(qapp: QApplication):
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
            assert _px(rb) == 14, rb.text()
        for combo in (
            dialog.combo_theme,
            dialog.combo_font_family,
            dialog.combo_rhi_backend,
        ):
            assert isinstance(combo, ComboBox)
            assert _px(combo) == 14
        assert _px(dialog.spin_max_length) == 14
    finally:
        dialog.close()


def test_settings_primary_labels_are_14px(qapp: QApplication):
    dialog = _dialog(qapp)
    try:
        assert isinstance(dialog.lbl_rhi_backend, Label)
        assert _px(dialog.lbl_rhi_backend) == 14
        assert dialog._keyboard_action_labels
        for name, _key in dialog._keyboard_action_labels:
            assert _px(name) >= 14, name.text()
    finally:
        dialog.close()


def test_settings_gallery_ai_page_is_14px(qapp: QApplication):
    dialog = _dialog(qapp)
    try:
        assert isinstance(dialog.gallery_ai_enabled, CheckBox)
        assert _px(dialog.gallery_ai_enabled) == 14
        for field in (
            dialog.gallery_ai_base_url,
            dialog.gallery_ai_api_key,
            dialog.gallery_ai_model,
        ):
            assert isinstance(field, CustomLineEdit)
            assert _px(field) == 14, field.placeholderText()
        # password echo + placeholder survive the font bump
        assert dialog.gallery_ai_api_key.placeholderText()
        from PySide6.QtWidgets import QLineEdit

        assert dialog.gallery_ai_api_key.echoMode() == QLineEdit.EchoMode.Password
    finally:
        dialog.close()


def test_settings_perf_extras_are_14px(qapp: QApplication):
    dialog = _dialog(qapp)
    try:
        assert isinstance(dialog.lbl_zoom_interp, Label)
        assert _px(dialog.lbl_zoom_interp) == 14
        assert isinstance(dialog.lbl_fps, Label)
        assert _px(dialog.lbl_fps) == 14
        assert _px(dialog.spin_fps) == 14
        dialog.spin_fps.setValue(60)
        assert dialog.spin_fps.value() == 60
    finally:
        dialog.close()


def test_settings_hints_and_search_stay_small(qapp: QApplication):
    """Secondary text is out of the sweep: hints/placeholders keep 11-12px."""
    dialog = _dialog(qapp)
    try:
        assert _px(dialog.lbl_rhi_backend_hint) <= 12
        for field in (dialog.search_field, dialog._keyboard_search):
            assert isinstance(field, CustomLineEdit)
            assert field.placeholderText(), "search field must keep its hint"
            assert _px(field) < 14
    finally:
        dialog.close()
