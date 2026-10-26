"""The magnifier button's focus log must not spam.

Owner report 2026-10-26: thousands of identical lines at ~1 ms apart —

    22:52:27,422 - [DEBUG] - (transient_magnifier.py:378) - [magnifier-visibility] btn_magnifier event=9 reason=FocusReason.MouseFocusReason
    ... (the same line ~1000x/s)

A closing window (or a popup re-focusing its anchor) hands focus back and forth,
and an unconditional ``logger.debug`` per FocusIn/FocusOut turns that into a wall
of identical text. The log is now throttled per (kind, reason): one line, then
silence for ``_FOCUS_LOG_MIN_INTERVAL_S``; a *different* kind/reason still logs,
and the same one logs again after a quiet gap — so a real later burst is not
hidden.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from PySide6.QtCore import QEvent, Qt
from tabs.image_compare.ui import transient_magnifier as tm


def _focus_event(kind, reason=Qt.FocusReason.MouseFocusReason):
    return SimpleNamespace(type=lambda: kind, reason=lambda: reason)


def test_repeated_focus_events_log_once(monkeypatch, caplog):
    monkeypatch.setattr(tm, "_FOCUS_LOG_SIG", None)
    monkeypatch.setattr(tm, "_FOCUS_LOG_TS", 0.0)
    caplog.set_level(logging.DEBUG, logger=tm.logger.name)

    for _ in range(50):
        tm._log_focus_event(_focus_event(QEvent.Type.FocusIn))

    lines = [r for r in caplog.records if "btn_magnifier event=" in r.getMessage()]
    assert len(lines) == 1, f"expected one throttled line, got {len(lines)}"


def test_a_different_reason_still_logs(monkeypatch, caplog):
    monkeypatch.setattr(tm, "_FOCUS_LOG_SIG", None)
    monkeypatch.setattr(tm, "_FOCUS_LOG_TS", 0.0)
    caplog.set_level(logging.DEBUG, logger=tm.logger.name)

    tm._log_focus_event(_focus_event(QEvent.Type.FocusIn))
    tm._log_focus_event(_focus_event(QEvent.Type.FocusOut))

    lines = [r for r in caplog.records if "btn_magnifier event=" in r.getMessage()]
    assert len(lines) == 2


def test_the_same_reason_logs_again_after_the_quiet_gap(monkeypatch, caplog):
    monkeypatch.setattr(tm, "_FOCUS_LOG_SIG", None)
    monkeypatch.setattr(tm, "_FOCUS_LOG_TS", 0.0)
    caplog.set_level(logging.DEBUG, logger=tm.logger.name)

    tm._log_focus_event(_focus_event(QEvent.Type.FocusIn))
    # pretend the quiet gap elapsed
    monkeypatch.setattr(tm, "_FOCUS_LOG_TS", tm.time.monotonic() - (tm._FOCUS_LOG_MIN_INTERVAL_S + 1))
    tm._log_focus_event(_focus_event(QEvent.Type.FocusIn))

    lines = [r for r in caplog.records if "btn_magnifier event=" in r.getMessage()]
    assert len(lines) == 2
