"""TEMP DEBUG probe: report UiMetrics channel state at test start."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_probe_channel_state():
    from sli_ui_toolkit.ui.managers.ui_metrics import UiMetrics

    m = UiMetrics.get_instance()
    print(
        f"[CHANNEL-PROBE] pending={m._pending} subs={len(m._subscriptions)}"
    )
