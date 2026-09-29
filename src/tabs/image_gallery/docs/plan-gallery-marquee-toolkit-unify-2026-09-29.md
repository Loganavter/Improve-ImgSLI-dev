# Plan: marquee toolkit-unify — one in-paint mechanism everywhere, no legacy

## Goal

One marquee mechanism for every consumer, Dolphin-style: pure tracker state +
band painted in the content host's own paint pass. Delete the window-overlay
path entirely (`MarqueeBandGesture`, `MarqueeBandOverlay`,
`map_content_rect_to_window`) and the gallery-local copy
(`tabs/image_gallery/ui/marquee_band.py`). No fallbacks, no compat shims.

Consumers (exhaustive, grepped 2026-09-29):
- toolkit `ui/widgets/composite/list_panel/widget.py:463` (own ListPanel)
- app `tabs/session_picker/recent/marquee.py` + `items_view.py`
- app `tabs/image_gallery/ui/marquee.py` + `marquee_band.py` (local copy) + `grid_view.py`
- exports: toolkit `widgets.py`, `overlays/__init__.py`; docs: `API_CATALOG.md:396`,
  `docs/dev/LOGGING.md` streams table (`SLI_MARQUEE_DEBUG` site cell)

## Non-goals

- No behavior change to commit semantics (shrink-wipe stays), selection
  visuals, translations, help, theme tokens.
- No autoscroll during band (still a follow-up).
- Toolkit version bump: no (unreleased accumulates per toolkit rules).

## Frozen seam (verbatim — all lanes, supervisor greps post-merge)

1. Toolkitparable API (canonical home: `sli_ui_toolkit/ui/widgets/overlays/marquee_state.py`):
   `MarqueeState(host, parent=None, min_drag_px=3, on_update=None, on_finish=None)`,
   `.active: bool`, `.app_filter_installed: bool`,
   `.start(content_pos: QPoint) -> bool`, `.update_at(content_pos) -> QRect` (pure),
   `.finish_at(content_pos) -> QRect` (pure, tiny→`QRect()`),
   `.cancel() -> None` (no `on_finish`), `.eventFilter(watched, event) -> bool`
   (moves `True`, LeftButton release finishes then `False`),
   `.set_accent(color)`, `.set_clip_widget(w)` (accepted no-op),
   `.set_on_update(cb)`, `.set_on_finish(cb)`.
   Trace injection (no host imports in toolkit): `on_trace: Callable | None`
   ctor kwarg; `[marquee]` lines via it, `SLI_MARQUEE_DEBUG` stays the var.
2. Band look contract (canonical paint helper in the same module):
   fill alpha 48 + 1px border alpha 200 of the accent, painted under children.
   Accent injected (`set_accent` / ctor), default `#0078D4`.
3. Host contract: host owns `band_rect: QRect | None` + `set_band_rect()`
   (equality-skip + region-limited `update(old ∪ new ±1px)`); band painted in
   the host's own paint pass after its fill. Toolkit ships a
   `MarqueeBandMixin` (or equivalent 3-line hook) so consumers don't
   reimplement; consumers never subclass overlay infra.
4. Routing: moves consumed while dragging; LeftButton release passes through.
5. Post-merge repo-wide grep gate (both repos):
   `MarqueeBandGesture|MarqueeBandOverlay|map_content_rect_to_window` → zero
   hits in `src/` + `tests/` (docs history may mention names in prose, never
   as imports).
6. `SLI_MARQUEE_DEBUG` var + `[marquee]` prefix preserved; equivalent trace
   lines ported (start/finish/tiny/cancel/filter/press-ignored-while-active).

## Wave 1 — Lane T (toolkit, single writer)

Owns (exclusive, repo `sli-ui-toolkit`):
- NEW `src/sli_ui_toolkit/ui/widgets/overlays/marquee_state.py`
  (tracker + paint helper/mixin, decoupled per §Frozen: no app imports)
- DEL `marquee_band_gesture.py`, `marquee_band_overlay.py`
- MOD `ui/widgets/overlays/__init__.py`, `src/sli_ui_toolkit/widgets.py`
  (+`__all__`), `ui/widgets/composite/list_panel/widget.py` (migrate to state),
  `tests/test_marquee_band.py` (port to state: behavior + pixel + release
  pass-through; rename to `test_marquee_state.py`, delete old file),
  `CHANGELOG.md` (Unreleased entry), `docs/dev/LOGGING.md` (site cell),
  `docs/user/API_CATALOG.md` (marquee row: state+paint, overlay names gone)
Phases: T1 port behavior tests green on new classes; T2 migrate ListPanel +
delete old modules + exports; T3 docs/changelog/mypy.
Acceptance (cwd = toolkit clone): full pytest suite green
(`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q -p no:cacheprovider`,
pre-existing `inspector_colors` fails if still present are reported, not fixed),
`mypy src/sli_ui_toolkit` zero NEW errors, grep gate §5 clean for toolkit.
Base: toolkit `feat/marquee-band-no-redundant-raise` HEAD (record SHA in prompt).

## Wave 2 — Lane A2 + Lane S (app, parallel after T merges locally)

Base: app `int/marquee-unify` (= `private/main` + perf `08069901` cherry-pick;
record SHA in prompts). Toolkit API available via installed editable package
(supervisor merges T locally first) — app lanes NEVER touch toolkit.

### Lane A2 (gallery switch)
Owns: `src/tabs/image_gallery/ui/marquee_band.py` (DELETE),
`src/tabs/image_gallery/ui/marquee.py` (import state from toolkit, drop local
holder; public names/signatures unchanged per inpaint-plan seam),
`src/tabs/image_gallery/ui/grid_view.py` (host: toolkit mixin/base instead of
local `MarqueeHost`; instantiation lines only),
`src/tabs/image_gallery/tests/test_marquee_*.py` (import updates only).
Acceptance: marquee quintet + gallery dir green; contracts file-size green;
pixel tests unchanged in meaning.

### Lane S (session_picker switch)
Owns: `src/tabs/session_picker/recent/marquee.py` (rewire to toolkit state;
module path kept),
`src/tabs/session_picker/recent/items_view.py` (host swap to band-capable
host + holder type; scoped hunks),
`src/tabs/session_picker/tests/runtime/test_recent_selection.py` (rewrite the
stale release expectation to the new contract: finish runs + release passes
through — this retires the known-failing test by replacing its premise).
Forbidden: `tabs/image_gallery/**` (Lane A2), toolkit.
Acceptance: recent-selection suite FULLY green (including the rewritten test);
no other session_picker suites broken.

## Execution notes (2026-09-29, supervisor)

- Lane A2 deviation: `marquee_band.py` kept as a THIN host shell
  (`MarqueeHost` + toolkit paint helper) instead of DELETE — the host half
  is consumer-owned by design (Dolphin: view paints itself); only the
  tracker was deduplicated. Same pattern in Lane S (`recent/marquee_host.py`).
- Headless-worker env lessons (4 dead attempts before takeover): never
  reference files outside the clone (session-root plan copy poisoned run 1);
  never send workers to inspect site-packages/pip (jail `external_directory`
  auto-reject kills them — run 2); toolkit cells MUST prefix test commands
  with `PYTHONPATH=<clone>/src` or pytest imports the supervisor's editable
  install (false green — caught in run 2). App cells are immune (imports
  resolve inside the clone).
- Wave 1 worker contributed the salvageable `MarqueeState` (+`on_trace`
  injection solving the logger two-gate trap); supervisor took over after
  attempt 2 per timebox rule and finished T/A2/S directly.

## Integration (supervisor)

One integration branch per repo (`int/marquee-unify` app; toolkit feat
branch), merge lanes sequentially, re-run: app gallery+session_picker suites
+ contracts; toolkit suite + mypy. Grep gate §5 on both merged trees.
One PR per repo at epic end from GitHub-wired checkouts (private mirror for
app). Cells removed same turn; `auto:` count 0 before any PR.

## Risks

- ListPanel migration unknowns (pre-flight: its content host + tests) — Lane T
  reads `list_panel/widget.py` + `ARCHITECTURE.md` first; if the host can't
  take paint, fallback is a toolkit `BandHostWidget` base (still no overlay).
- Hover gates (`hover.py`, shelf gates) read `.active`/`.app_filter_installed`
  — preserved by seam §1, no edits needed.
- `map_content_rect_to_window` external users: none found (only gesture +
  tests) — safe to delete with the module.
