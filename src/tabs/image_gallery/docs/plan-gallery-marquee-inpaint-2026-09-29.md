# Plan: gallery marquee in-paint band (Dolphin-style)

## Goal

Replace the gallery marquee's window-level overlay widget with a band painted
in the content host's own paint pass, Dolphin-style. One widget dies
(`MarqueeBandOverlay` on the gallery path), one paint pass remains.

Proven by the 2026-09-29 traces (log `~/.local/share/ImproveImgSLI/log.txt`,
sessions 14:15–14:28):
- single overlay object, balanced show/hide — yet nested/shifted double
  borders on screen (`H2: two overlays` killed, ghost unexplained by overlay
  state);
- mid-drag `hide reason=invalid` flicker (clip round-trip) while the drag
  continues;
- release position ≠ last move position after a hold → tiny rect → `paths=0`
  → non-additive replace wipes the selection ("dies on shrink");
- `DOUBLESEL-HOVERBAR` fired: hover bar paints on bg-locked (selected) cards.

Dolphin reference (`../dolphin`, this machine):
`private/kitemlistrubberband.cpp` (76 lines, pure state: start/end/active +
signals) + band painted in the view's own `paintEvent` via
`CE_RubberBand` (`kitemlistview.cpp:953-968`); scroll compensated at set/use
time (`kitemlistcontroller.cpp:682-688,1385`); degenerate start==end forced
to ±1px (no invalid states); hit-test against layout rects. No overlay, no
restack, no cross-space mapping — event rate is irrelevant (Qt compresses
`update()` to frame rate).

## Non-goals

- Toolkit untouched (`MarqueeBandGesture`/`MarqueeBandOverlay` stay for the
  session-picker path). No `sli-ui-toolkit` lane.
- No autoscroll during band (Dolphin has it; here a follow-up, not this plan).
- No change to commit semantics: shrink-to-empty still replaces with the hit
  set (including `paths=0` wipe) — pinned by tests, UX verdict separate.
- No change to selection visuals except Lane B's bar gate. No translations,
  no help pages, no theme tokens.

## Area + base branch

- Area: `src/tabs/image_gallery/ui/marquee.py`, new `src/tabs/image_gallery/ui/marquee_band.py`,
  `src/tabs/image_gallery/ui/grid_view.py` (host swap + paint trigger hunks only),
  `src/tabs/image_gallery/ui/card/painters.py` (Lane B), gallery marquee tests.
- Base: `feat/marquee-update-debug` HEAD at launch (record SHA in worker
  prompts). Only the supervisor integrates into it.

## Ownership (disjoint — max 2 write lanes)

| Lane | Task | `owns_files` (exclusive) |
|---|---|---|
| A `lane-marquee-inpaint` | in-paint band refactor (phases A1–A4) | `src/tabs/image_gallery/ui/marquee.py`, `src/tabs/image_gallery/ui/marquee_band.py` (new), `src/tabs/image_gallery/ui/grid_view.py`, `src/tabs/image_gallery/tests/test_marquee_*.py` (new + existing marquee tests) |
| B `lane-hoverbar-gate` | hover-bar mutual exclusion + probe removal (phases B1–B2) | `src/tabs/image_gallery/ui/card/painters.py` |

Lane A must not touch `painters.py`. Lane B must not touch `marquee*.py` /
`grid_view.py` / tests outside a new `test_card_hoverbar_gate.py` (if needed,
same dir — Lane A owns `test_marquee_*` only, no overlap by filename).

## Frozen seam (verbatim — both lanes + supervisor verify)

1. Selection API unchanged, same call shapes:
   `commit_preview(owner, paths, additive=additive)`,
   `sel.commit(owner, paths, additive=additive)`,
   `view.apply_selection(preview)`.
2. `ui/marquee.py` public names stay importable with identical signatures:
   `ensure_marquee_gesture(view)`, `paths_for_rect(view, rect)`,
   `paths_for_marquee_rect(view, rect)`, `on_rect_update(view, rect)`,
   `on_rect_finish(view, rect)`, `event_filter(view, watched, event)`,
   `host_mouse_press(view, event)`, `marquee_disabled()`.
   (`ensure_marquee_gesture` may return the state holder; tests calling
   `on_rect_update(view, band)` keep working.)
3. `view._marquee_gesture` attribute keeps existing; the holder exposes
   `.active: bool` and `.app_filter_installed: bool` so `hover.py` gates
   (`idle/active/filter`) keep reporting without edits to `hover.py`.
4. Mouse routing semantics preserved: moves consumed while dragging,
   LeftButton release passes through (`return False`) — the hover-loss fix
   (`inv-gallery-hover-loss-2026-09-26`) must not regress.
5. Band look preserved: fill alpha 48 + 1px border alpha 200 of the selection
   accent (same colors the overlay used), painted under cards (children paint
   later) — Dolphin parity.
6. Curated debug stays: `IMGSLI_GALLERY_DEBUG` lines in `marquee.py` /
   `context_menu.py` / `marquee_snapshot.py` are kept (they are the requested
   diagnostics, not temporary). The `DOUBLESEL-HOVERBAR` probe in
   `painters.py` is TEMPORARY — Lane B removes it as part of the fix.

## Lane A phases

### A1 — pin behavior with regression tests (before any src change)

New `src/tabs/image_gallery/tests/test_marquee_band_contract.py`:
- update/finish plumbing: `on_rect_update` dispatches preview, identical
  membership coalesces, `on_rect_finish` commits via owner with
  `(paths, additive)`; empty non-additive finish clears (COMMIT-EMPTY);
  tiny-drag (`1x1`) finishes empty (current `min_drag` semantics pinned).
- release pass-through: tracker `eventFilter` returns `False` on LeftButton
  release while still finishing (hover-loss contract at gallery level).
- mapping: band rect == `QRect(origin, pos).normalized()` in host coords
  (no window round-trip in the new path — assert content-space identity).
Verify: new test green on OLD code where semantics already hold; where the
new path differs (mapping), mark `xfail`-free stand-ins that pass only
post-refactor — no, simpler: write mapping/pixel tests to pass post-A2,
behavior tests to pass pre- AND post-A2 (prove no semantic drift).

### A2 — state holder + host paint + swap (core refactor)

New `src/tabs/image_gallery/ui/marquee_band.py`:
- `MarqueeState(QObject)`: `_origin: QPoint | None`, `active` property,
  `app_filter_installed` flag, `start(content_pos) -> bool`,
  `update_at(content_pos) -> QRect`, `finish_at(content_pos) -> QRect`
  (tiny→`QRect()` included, same `min_drag_px=3` rule), `cancel()`.
  Dolphin rules ported: degenerate start==end nudged ±1px (never invalid);
  `cancel()` hides without `on_finish`.
- `MarqueeHost(OpaqueFillHost)` subclass: `band_rect: QRect | None` +
  `set_band_rect()` (assign + `update()`, skip when equal — no restack, no
  show/hide, no stacking calls at all); `paintEvent`: base fill first, then
  band fill+border when rect valid/non-empty.
- `marquee.py` rewiring: tracker keeps app-filter move/release handling with
  identical routing semantics; visual side calls `host.set_band_rect()` and
  `on_rect_update/on_rect_finish` unchanged; overlay creation removed from
  the gallery path (`ensure_marquee_gesture` returns/keeps the holder).
- `grid_view.py`: instantiate `MarqueeHost` instead of `OpaqueFillHost`
  (lines ~201-206); nothing else.
Verify: A1 behavior tests green unmodified; offscreen pixel tests —
band painted at cursor (grab host, accent pixels inside expected rect),
shrink big→small leaves zero stale pixels in the exposed region (the probe
from 2026-09-29, now a regression test); full gallery marquee suites green.

### A3 — scroll/edge unification + degenerate cases

- No clip round-trip: host paint clips inherently; hit-test uses the same
  content rect the band shows (clip-vs-hit divergence class deleted).
- Drag outside host: band paints the intersected visible part implicitly
  (paint clipped by widget bounds); no `invalid` hide/show flicker possible
  (no visibility toggling mid-drag — paint skips empty rects silently).
- Press refusal paths keep logging (`REFUSE button/no-host/child`).
Verify: offscreen drag-out-of-host test (band stays in bounds, no invalid
states); `SLI_MARQUEE_DEBUG`-independent (toolkit flag no longer needed on
the gallery path — document in the plan close-out note).

### A4 — menu interplay + docs close-out

- Context menu opens/closes freely mid- or post-drag: no overlay state to go
  stale; `marquee_snapshot.py` simplified to gesture active/idle + band rect
  (overlay fields dropped).
- Regenerate `docs/dev/DOC_INDEX.md` via
  `python src/devtools/docs_link_graph.py --write-index` (this plan file is
  new under `src/tabs/*/docs/`).
- Keep curated `IMGSLI_GALLERY_DEBUG` lines; remove nothing else.
Verify: menu open/hide log shows `idle` on both sides; contracts green.

## Lane B phases

### B1 — gate the bar on selection lock

In `painters.py` bar branch: skip the hover bar when the card is selected
(`is_bg_locked()` true) — fill already signals selection; the bar is the
proven double signal. One-line-class change, fail-open preserved.
Verify: offscreen pixel — selected+hovered card paints no bar-band pixels;
new or existing card test pins it.

### B2 — remove the TEMPORARY probe + verify silence

Delete the `DOUBLESEL-HOVERBAR` block. Repro run must show no such line
while the bar-gate test stays green.
Verify: `grep DOUBLESEL-HOVERBAR` empty in tree; card suites green.

## Env / falsification matrix (method)

- Offscreen (`QT_QPA_PLATFORM=offscreen`) for geometry/pixel contracts
  (blindness noted 2026-09-29: hover wash needs live Enter — bar-gate test
  drives `_hover_blue_bar` directly instead).
- Live Wayland repro for ghost/shake (cannot be proven offscreen): big drag
  → shrink → release; menu open/hide on selected card.
- Kill conditions: A2 pixel tests fail → band misplaced (stop, do not
  proceed to A3); DOUBLESEL reappears post-B2 → gate incomplete.

## Risks / guards

- Release routing regression (hover death) — pinned by A1 pass-through test.
- `MarqueeHost` vs shared `OpaqueFillHost`: subclass, never modify the
  shared class (session shelf unaffected).
- File-size contract (500): new modules stay small; no `try/except` padding
  around fail-open helpers.
- Session-picker marquee (`tabs/session_picker/recent/marquee.py`) is OUT —
  its runtime test `test_empty_host_press_starts_in_window_marquee` fails
  pre-existing (stale expectation vs toolkit pass-through, `d792c9f`); lanes
  must not touch it, report as-is.
- No `auto:` commits in final diff; lanes push bare branches only.

## Supervisor close-out

Claimed-vs-real per worker DONE (read files at cited lines, re-run named
suites on merged tree, grep `INTERFACE:` symbols for duplicates), merge
lanes sequentially into integration, full gallery suites + contracts,
`agent-clone.sh remove` same turn, PR from GitHub-wired checkout.
