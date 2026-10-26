"""Reset the Image Gallery's measured-metrics caches and re-enter the pipeline.

Backs the card context menu's **Reset metrics cache** entry and the Find
Action / MCP ``gallery.reset-metrics`` descriptor.

Deleting the disk cache files alone is a **no-op**: the Stage-2 measured pass
is gated by an in-memory content fingerprint
(``owner._last_analysis_fingerprint`` — see
``use_cases.proxy_pass._apply_triage_result``) and the AI domain is cache-first
(``services.ai_cache.hydrate_item`` memoizes an "already checked" verdict on
the item, scoped to the identity it was earned under, and
``use_cases.ai_analysis.analyze_item`` short-circuits on
``load_cached_analysis``). A genuine recompute therefore has to clear, in ONE
place:

* the in-memory per-item artifact/metric/analysis state + the local activity
  phase;
* the in-memory proxy decode cache (``services.proxy.clear_proxy_cache``);
* the on-disk AI scorecards (``services.ai_cache``) and the VLM metric-profile
  pins (``services.profile_cache``);
* the stored metric profile (``owner.clear_metric_profile``) and the Stage-2
  fingerprint.

The cleared item state includes the **metric-derived rank state** (``rank`` /
``rank_source`` / ``crown_rank`` / ``is_best`` / badge triple), not just the
numbers: a reset asks for a fresh UNRANKED view, so both an automatic
(fusion/jev) rank and an explicit "Make best" pick go — the manual pick is a
rank OVER the old measurements. ``series_id`` / ``provenance_series_id`` /
``rejected`` / ``triage_rejected`` are not metric-derived and survive.

The clear then re-stamps the badges unranked (``rank_badge.stamp_badges(...,
show_rank=False)``) and refreshes the bound cards through the live view
(``refresh_cards``) — otherwise the per-card painted dots
(``_gallery_dot_colors``) and the ★ BEST pill survive on screen even though
the items are already empty (the painted view is not derived from the items
at paint time, it is stamped at build/update time).

``reset_metrics_caches`` (the user-facing action) then stops. OWNER DECISION
2026-10-22: the reset ZEROES, it does not re-run (see that function).

**The reset is a HARD BARRIER** (owner decision 2026-10-26): the clear advances
two current-work tokens *before* it touches anything — ``_domain_epoch`` (the
judgment-domain token: AI / Jev / profile / series-priority / pairwise) and
``_analysis_epoch`` (the measured-metrics token: Stage-2 proxy, triage, the
per-stage producers). Every such worker snapshots its token at start and drops
its delivery when the token moved, so a result produced before the reset cannot
land afterwards in memory, on disk (``save_analysis`` / ``local_metrics.persist``)
or on a card. The in-flight ledgers (batch, phase markers, stage gate, judge
run, AI queue) are retired in the same step — see
``use_cases/reset_barrier.clear_delivery_ledgers``.

EVERY measurement cache is dropped, INCLUDING the Jev rank pins and the
tie-break briefs (``services.jev_cache`` / ``services.vlm_cache``) on disk and
their in-memory halves (``state.tie_breaks`` / ``state.series_priority`` plus
each item's ``vlm_tie_*`` / ``vlm_brief_*`` fields). The owner's order
(2026-10-22) is literal: the action zeroes all measured state without caveats.
The earlier version deliberately kept them ("their keys change anyway") and the
result read as a partial reset — a pinned rank or brief survived and looked
like a stale measurement.

The scope is the WHOLE POOL, not the menu selection: a per-card reset leaves
every other card's numbers in place, which is indistinguishable from "nothing
happened" (owner report 2026-10-22). Callers pass ``paths=None``.

Audit-Meta: pattern=reset-barrier size=535 reason="one reset contract: the two current-work tokens, every in-memory/on-disk clear and the visible re-stamp must happen in ONE order (token first, then clear, then repaint); splitting them lets a delivery land between the steps — the exact defect the barrier removes."
"""

from __future__ import annotations

import logging
from pathlib import Path

from tabs.image_gallery.models import AnalysisStatus
from tabs.image_gallery.services import jev_cache, vlm_cache
from tabs.image_gallery.services.activity import clear_activity
from tabs.image_gallery.services.rank_badge import KIND_NONE, stamp_badges
from core.log_names import APP_LOGGER_NAME

logger = logging.getLogger(APP_LOGGER_NAME)


def _state_of(owner):
    """The owner's gallery state (``owner.state``, else the widget's ``_state``).

    A controller in production owns ``state``, but the widget itself is a legal
    owner (storeless/live-menu paths) and carries ``_state`` instead — the same
    probe ``_items_of`` delegates to, so the in-memory half of a reset reaches
    the same object the cleared items came from.
    """
    try:
        st = getattr(owner, "state", None)
        if st is not None:
            return st
        widget = getattr(owner, "widget", None) or getattr(owner, "_widget", None)
        if widget is None:
            return None
        return getattr(widget, "_state", None) or getattr(
            getattr(widget, "_controller", None), "state", None
        )
    except Exception:
        return None


def _items_of(owner) -> list:
    """The owner's pool items (``state.items`` first, widget fallback)."""
    try:
        return list(getattr(_state_of(owner), "items", None) or [])
    except Exception:
        return []


def _path_key(item) -> str:
    try:
        return str(getattr(item, "path", ""))
    except Exception:
        return ""


def _clear_item(item) -> None:
    """Drop one item's measured / AI / metric-derived rank state.

    DECISION: a metrics reset is a *reset*, not a cache refresh. Auto ranks
    (``fusion``/``jev``) and a manual "Make best" pick both go — the user
    asked for a fresh unranked view, and a manual pick is a rank over the old
    measurements (leaving ``triage_best`` set would let the next snapshot
    re-freeze it as a manual rank and silently undo the reset). What is NOT
    metric-derived survives: ``series_id`` / ``provenance_series_id`` (group
    identity), ``rejected`` / ``triage_rejected`` (user triage decisions).
    """
    try:
        item.metrics = {}
        item.artifacts = {}
        item.artifact_maps = {}
        item.analysis = None
        item.analysis_status = AnalysisStatus.NOT_ANALYZED
        item.analysis_error = None
        # Engine records + the k-draw scorecards are MEASUREMENTS too: leaving
        # them meant the read path (``analysis.read``) still answered from the
        # old pass after the reset (owner: "метрики остались").
        item.analysis_records = ()
        # Metric-derived rank state — see the DECISION above.
        item.rank = None
        item.rank_source = None
        item.crown_rank = None
        item.is_best = False
        item.triage_best = False
        item.triage_rank = None
        item.badge = ""
        item.badge_kind = KIND_NONE
        item.badge_source = ""
        # Stage-3 VLM verdicts + briefs: a tie-break/compare answer is a
        # MEASUREMENT produced by the paid judge, so it goes with the rest.
        # ``vlm_brief_status`` returns to its dataclass default ("none"), not
        # to a "pending" state — the reset leaves nothing measuring.
        item.vlm_tie_result = None
        item.vlm_tie_pending = False
        item.vlm_tie_error = None
        item.vlm_brief = None
        item.vlm_brief_status = "none"
        item.vlm_brief_error = None
    except Exception:
        logger.debug("metrics reset: item state clear failed", exc_info=True)
    try:
        # Both halves of the hydrate memo: the flag AND the identity it was
        # earned under, so the next populate reads the (now deleted) entry
        # instead of short-circuiting on a stale "checked" verdict.
        item._ai_cache_checked = False
        item._ai_cache_checked_identity = None
    except Exception:
        pass
    try:
        clear_activity(item, "local")
    except Exception:
        pass


def _cards_view(owner):
    """The live view that owns the card widgets, or ``None`` (storeless tests).

    Owner is a controller in production (``owner.widget``), but the widget
    itself is also a legal owner (storeless/live-menu paths), so both are
    probed. A bare ``_grid_view`` is the last resort for thin doubles.
    """
    try:
        candidates = (getattr(owner, "widget", None), getattr(owner, "_widget", None), owner)
    except Exception:
        return None
    for cand in candidates:
        if cand is None:
            continue
        try:
            if callable(getattr(cand, "refresh_cards", None)):
                return cand
            grid = getattr(cand, "_grid_view", None)
            if grid is not None and callable(getattr(grid, "refresh_cards", None)):
                return grid
        except Exception:
            continue
    return None


def _source_path_of(owner, view):
    """Current source hub for the badge stamp (identity badge stays visible)."""
    for cand in (owner, view, getattr(owner, "widget", None)):
        if cand is None:
            continue
        try:
            src = getattr(cand, "_source_path", None)
        except Exception:
            src = None
        if src is not None:
            return src
    return None


def _refresh_cleared_view(owner, targets) -> None:
    """Re-stamp the cleared items unranked and repaint their cards.

    The dots and the ★ BEST pill are stamped ON the card at build/update time
    (``ui/card.py``), so mutating the items alone leaves the painted view
    showing the old colours until some unrelated event repaints it. Two
    existing seams, no new render pipeline: the single badge-stamp point
    (``stamp_badges``, ``show_rank=False`` — the ranking is not final after a
    reset) and the view's targeted per-card update (``refresh_cards``, the
    same path a triage tail uses, which recomputes ``_gallery_dot_colors``
    from the now-empty metrics). Never raises.
    """
    try:
        clear_targets = list(targets or [])
    except Exception:
        return
    if not clear_targets:
        return
    view = _cards_view(owner)
    try:
        stamp_badges(clear_targets, _source_path_of(owner, view), show_rank=False)
    except Exception:
        logger.debug("metrics reset: badge re-stamp failed", exc_info=True)
    # The OPEN quick-look report holds its own row set: it must rebuild from the
    # cleared items, or the reset looks like a no-op while the panel still shows
    # the old numbers (owner 2026-10-22: "кэш сброшен, нумерации нет, а метрики
    # остались").
    try:
        refresh_ql = getattr(owner, "_refresh_open_quick_look", None)
        if callable(refresh_ql):
            refresh_ql()
    except Exception:
        logger.debug("metrics reset: quick-look refresh failed", exc_info=True)
    if view is None:
        return
    try:
        view.refresh_cards(clear_targets)
        return
    except Exception:
        logger.debug("metrics reset: batch card refresh failed", exc_info=True)
    for it in clear_targets:
        try:
            view.refresh_card(it)
        except Exception:
            logger.debug("metrics reset: per-card refresh failed", exc_info=True)


def clear_metrics_caches(owner, *, paths=None) -> dict:
    """Clear the measured-metrics caches (in-memory + disk). Never raises.

    *paths* narrows the per-item clear (the card menu passes its file-manager
    targets); ``None`` means every item of ``owner.state.items`` and a
    whole-directory AI-scorecard sweep (``ai_cache.clear_all``). The profile,
    Jev and VLM stores are ALWAYS swept whole-directory: their entries are
    keyed by series/pair identity, not by one card's path, so a scoped delete
    cannot express "drop the pins this card was part of". Returns an honest
    summary: ``{"items": n, "ai_files": n, "profiles": n, "jev_files": n,
    "vlm_files": n}`` — the last two are the Jev rank pins and the VLM
    tie-break/brief files actually unlinked.

    Cleared items lose their metric-derived rank state AND their VLM verdict /
    brief fields (see :func:`_clear_item`); the in-memory verdict maps
    (``state.tie_breaks``, ``state.series_priority``) are emptied as well — the
    Jev hint through the controller's own seam, so the per-series attention
    marker is re-stamped too — and the bound cards are re-stamped unranked and
    repainted BEFORE this returns; a reset must look reset immediately, not
    after the async pass repaints.

    A HARD BARRIER: the first action advances both current-work tokens and
    retires the in-flight ledgers (``use_cases.reset_barrier`` /
    :func:`~tabs.image_gallery.use_cases.reset_barrier.clear_delivery_ledgers`),
    so no pre-reset delivery can land after this returns.
    """
    summary = {"items": 0, "ai_files": 0, "profiles": 0, "jev_files": 0, "vlm_files": 0}
    # HARD BARRIER (owner decision 2026-10-26), BEFORE any clear: advance the
    # two current-work tokens and retire the in-flight ledgers. A delivery that
    # races the clear is stale from this line on, and the ledgers it would
    # consult (settled/phase/stage/judge/queue) no longer describe this world.
    from tabs.image_gallery.use_cases import reset_barrier as _reset_barrier

    _reset_barrier.bump_delivery_epochs(owner)
    _reset_barrier.clear_delivery_ledgers(owner)
    items = _items_of(owner)
    if paths is None:
        targets = items
    else:
        wanted = set()
        for p in paths or ():
            try:
                wanted.add(str(Path(p)))
            except Exception:
                continue
        targets = [it for it in items if _path_key(it) in wanted]
    for it in targets:
        _clear_item(it)
        summary["items"] += 1

    # In-memory decode cache: the proxy pass re-decodes from scratch.
    try:
        from tabs.image_gallery.services import proxy as _proxy

        _proxy.clear_proxy_cache()
    except Exception:
        logger.debug("metrics reset: proxy cache clear failed", exc_info=True)

    # Disk caches: AI scorecards + the VLM metric-profile pins.
    try:
        from tabs.image_gallery.services import ai_cache as _ai_cache

        if paths is None:
            summary["ai_files"] = int(_ai_cache.clear_all())
        else:
            removed = 0
            for it in targets:
                try:
                    if _ai_cache.clear_cached_analysis(it.path, it.mtime_ns):
                        removed += 1
                except Exception:
                    continue
            summary["ai_files"] = removed
    except Exception:
        logger.debug("metrics reset: ai cache clear failed", exc_info=True)
    try:
        from tabs.image_gallery.services import profile_cache as _profile_cache

        summary["profiles"] = int(_profile_cache.clear_default_cache())
    except Exception:
        logger.debug("metrics reset: profile pin clear failed", exc_info=True)
    # Jev rank pins + VLM tie-break/brief files: measured decisions, so a
    # "zero all measurements" reset drops them (owner order 2026-10-22). Both
    # helpers delete only their own file patterns and never raise; the counts
    # are part of the returned summary because "how much was dropped" is the
    # only observable proof the action did anything on disk.
    summary["jev_files"] = int(jev_cache.clear_default_cache())
    summary["vlm_files"] = int(vlm_cache.clear_default_cache())
    # The IN-MEMORY halves of those two stores. An open session paints the
    # pinned Jev ordering and the VLM verdicts from ``state`` without reading
    # disk again, so dropping the files alone left the stale measurements on
    # screen until the process restarted — the partial-reset complaint this
    # whole function exists to answer.
    try:
        st = _state_of(owner)
        if st is not None:
            st.tie_breaks = {}
            st.series_priority = {}
    except Exception:
        logger.debug("metrics reset: in-memory verdict clear failed", exc_info=True)
    # The Jev routing hint also paints a per-series-header attention marker, so
    # prefer the controller's own clear seam (it drops the hint AND re-stamps
    # the headers); ``state.series_priority`` above already covers owners that
    # have no such seam.
    try:
        clear_priority = getattr(owner, "_clear_series_priority", None)
        if callable(clear_priority):
            clear_priority()
    except Exception:
        logger.debug("metrics reset: series priority marker clear failed", exc_info=True)
    # The LOCAL Stage-2 result is a measurement cache too: left on disk, the
    # next triage hydrates it straight back and the reset looks like a no-op
    # (the exact failure the AI-scorecard clear above exists to prevent).
    # Deliberately no ``summary`` key: ``test_metrics_cache_reset`` asserts the
    # summary dict EXACTLY, and the count is diagnostic, not an API.
    try:
        from tabs.image_gallery.services import metrics_cache as _metrics_cache

        if paths is None:
            dropped = int(_metrics_cache.clear_all())
        else:
            dropped = sum(
                1
                for it in targets
                if _metrics_cache.clear_local_metrics(it.path, it.mtime_ns)
            )
        logger.debug("metrics reset: local metrics entries dropped=%d", dropped)
    except Exception:
        logger.debug("metrics reset: local metrics clear failed", exc_info=True)
    # The selection profile's generation markers: a reset re-opens the selector
    # for the SAME folder generation (the frozen/consumed guard would otherwise
    # suppress it after the first run).
    try:
        owner._profile_consumed_gen = None
        owner._profile_settle_pending_gen = None
    except Exception:
        pass

    # Stored profile + the Stage-2 skip gate.
    try:
        clear = getattr(owner, "clear_metric_profile", None)
        if callable(clear):
            clear()
    except Exception:
        logger.debug("metrics reset: clear_metric_profile failed", exc_info=True)
    try:
        owner._last_analysis_fingerprint = None
    except Exception:
        logger.debug("metrics reset: fingerprint clear failed", exc_info=True)

    # Visible reset LAST: the profile is already dropped, so the refreshed
    # dots use the fresh (mode-derived) axis set, and the cards show the
    # unranked/neutral state the re-entered pass starts from.
    _refresh_cleared_view(owner, targets)
    try:
        from tabs.image_gallery.debug import gallery_debug as _dbg

        _dbg(
            "metrics reset: scope=%s items=%d ai_files=%d profiles=%d "
            "jev_files=%d vlm_files=%d",
            "pool" if paths is None else f"{len(targets)} card(s)",
            summary["items"],
            summary["ai_files"],
            summary["profiles"],
            summary["jev_files"],
            summary["vlm_files"],
        )
    except Exception:
        pass
    return summary


def reset_metrics_caches(owner, *, paths=None) -> dict:
    """Clear the caches, then RE-ENTER the triage rebuild. Never raises.

    ``paths`` is accepted for API compatibility but a RESET is always the whole
    pool (owner decision 2026-10-22): a scoped reset left the rest of the grid
    looking untouched, which reads as a broken button.

    OWNER DECISION 2026-10-22: the action ZEROES, it does not re-run. The
    earlier version re-entered the triage rebuild, so the numbers (and with them
    the AI/ALG marker) came back seconds later — or on the next repaint (opening
    and closing quick look) — which reads exactly like "the reset did not
    work". A reset now leaves an empty, unranked gallery; the ordinary triggers
    (open the folder, Analyze, the folder's next triage) recompute from scratch
    because the Stage-2 fingerprint and every disk cache were dropped.

    ``summary["requeued"]`` is kept for callers and is always ``False``.
    """
    paths = None
    summary = clear_metrics_caches(owner, paths=paths)
    summary["requeued"] = False
    return summary
