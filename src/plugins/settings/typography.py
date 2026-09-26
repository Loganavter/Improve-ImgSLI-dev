"""Settings typography — three font groups for the settings dialog.

Every settings page (built-in ``plugins/settings/pages/*`` and tab-owned
extras/sections) sizes its text through these groups instead of hardcoded
``pixel_size=`` literals, so the whole dialog scales as one system:

- ``TITLE`` (18px) — group/fieldset titles (``CustomGroupWidget`` captions).
- ``BODY`` (16px) — primary content: checkboxes, radios, combos, line edits,
  spins, sliders' labels and primary row labels.
- ``CAPTION`` (14px) — secondary text: restart hints, warnings, footnotes.

Toolkit-owned chrome (sidebar rows, search field, ``Button`` family, dialog
action bar) is intentionally out of scope — those widgets own their sizing
via the painter pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sli_ui_toolkit.ui.managers.ui_font import apply_ui_font
from sli_ui_toolkit.widgets import CustomGroupWidget, Label

if TYPE_CHECKING:
    from PySide6.QtGui import QFont

#: Group/fieldset titles.
SETTINGS_TITLE_PX = 18
#: Primary content: checkboxes, radios, combos, edits, spins, row labels.
SETTINGS_BODY_PX = 16
#: Secondary text: hints, warnings, footnotes.
SETTINGS_CAPTION_PX = 14


def apply_settings_title(widget: CustomGroupWidget) -> QFont:
    """Pin a group widget's title to the ``TITLE`` group.

    ``CustomGroupWidget`` paints its caption from ``widget.font()``, so
    setting the widget font sizes the title (the painter already forces
    bold).
    """
    return apply_ui_font(widget, pixel_size=SETTINGS_TITLE_PX)


def apply_settings_body(widget) -> QFont:
    """Pin a primary control to the ``BODY`` group."""
    return apply_ui_font(widget, pixel_size=SETTINGS_BODY_PX)


def apply_settings_caption(widget) -> QFont:
    """Pin a secondary control to the ``CAPTION`` group."""
    return apply_ui_font(widget, pixel_size=SETTINGS_CAPTION_PX)


def settings_group(dialog, search_group: object) -> CustomGroupWidget:
    """Build a title-styled group widget from a settings ``SearchGroup``.

    Same as ``search_group.widget(dialog)`` plus the ``TITLE`` font — the
    single entry point every settings page uses for its fieldsets.
    """
    widget = search_group.widget(dialog)  # type: ignore[attr-defined]
    apply_settings_title(widget)
    return widget


def settings_body_label(text: str, parent=None, **kwargs) -> Label:
    """Primary row label in the ``BODY`` group."""
    return Label(text, pixel_size=SETTINGS_BODY_PX, parent=parent, **kwargs)


def settings_caption_label(text: str, parent=None, **kwargs) -> Label:
    """Secondary hint/warning/footnote label in the ``CAPTION`` group."""
    return Label(text, pixel_size=SETTINGS_CAPTION_PX, parent=parent, **kwargs)
