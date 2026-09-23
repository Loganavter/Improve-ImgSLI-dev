# Plan: Quick look S4 visual parity close-out (LIGHT)

Status: `draft` · Date: 2026-09-23 · Owner: @jorj
Base branch: `int/gallery-light` (HEAD `7e2e8776` at plan time; workers record base SHA in prompt)
Tracked in internal-docs: `docs/backlog/queue.yaml` (tasks `gallery-ql-s4-w1`, `gallery-ql-s4-w2`)
Design authority: `design/ui-mockup-v4-quicklook-light.svg` (S4 v2)
Prior plan: `plan_mockup_parity_2026-09-22.md` (waves A–D merged; VLM Pass-2 explicitly non-goal there — inherited here)
Recon evidence: supervisor-verified `file:line` table (2026-09-23 chat recon, 3 agents + supervisor code checks)

## Goal / non-goals

**Goal:** make the rendered quick look overlay match S4 v2 LIGHT: dimmed grid behind a
1040×620 card, live fidelity numbers (no stale `— · not measured`), thumbnail strip with
real thumbs + overlaid badges, visible banding base, no `SHARPNESS CROP` in fidelity mode,
numeric `vs #N` brief fallback visible whenever metrics exist, `upscale ×N` in meta.

**Non-goals (explicit):**
- VLM brief prose (`ridge detail…`, `HF −31%` narrative) — unwired pipeline
  (`controller.py:850` orphan, `vlm.py:270` never called); stays numeric fallback per
  prior plan's VLM non-goal. No identity impact: fallback only reads `item.metrics`.
- AI tie-break badge without AI config — stays hidden; `tie-break pending` copy unchanged.
- `mild · sky region` copy — intentionally severity-only (P0-8, no region analysis exists).
- Promoting tokens into `sli-ui-toolkit` — separate repo/task. Toolkit needs **no**
  changes (strip fix is app-side via documented `regions=[ButtonRegion(pixmap=…)]`).
- `themes.json` global retoken — W1 must NOT touch it; use existing
  `gallery.card.background` token like grid cards do.

## Area

`src/tabs/image_gallery/ui/quick_look.py`, `ui/quick_look/{helpers,strip,bars,histograms,artifacts,source_inset}.py`,
`ui/quick_look_hooks.py`, `controller.py`, `services/fidelity_metrics.py`,
`tests/test_quick_look_parity.py`, `tests/runtime/test_gallery_truth.py`.
Base branch: `int/gallery-light`.

## Ownership (2 parallel writers, disjoint, cap respected)

| Wave | Owner | Owns files | Scope |
|---|---|---|---|
| W1 chrome | @ql-s4-w1 | `ui/quick_look.py`, `ui/quick_look/{helpers,strip,bars,histograms,artifacts,source_inset}.py`, `tests/test_quick_look_parity.py` | dim veil paintEvent (mirror `ui/clean_review.py:55-59,321-337`), card plate fill/border/rx via painter pipeline (token `gallery.card.background`, no QSS), prev/next 36px circles at card edge, strip thumbs via `regions=[ButtonRegion(pixmap=…, image_fill="cover")]` (drop unsupported `pixmap=` kwarg on `Button`), banding base visible in light, `SHARPNESS CROP` gated to non-fidelity modes, implement `refresh_metrics` |
| W2 pipeline | @ql-s4-w2 | `controller.py`, `services/fidelity_metrics.py`, `ui/quick_look_hooks.py`, `tests/runtime/test_gallery_truth.py` | `_on_fidelity_ready` refreshes open overlay (mirror `_on_artifacts_ready`), `Set as source` (overlay/hook/context-menu paths) re-runs fidelity or marks stale, no behavior change to metric math |

`check_queue_lock.py` passes: distinct `relates_to` anchors + disjoint `owns_files`.

## Seam interface (verbatim in both worker prompts; no second implementation)

- `QuickLookOverlay.refresh_metrics(self, item) -> None` — **W1 implements**
  (mirrors `refresh_artifacts`; rebuilds metrics + meta + brief for the open overlay,
  no-op when hidden). **W2 calls** it from `_on_fidelity_ready` and the set-source
  paths. W2 MUST NOT define its own overlay-refresh helper.
- `item.metrics` fidelity keys (unchanged): `ssim ∈ [0,1]`,
  `hf_ratio = hf_out/hf_in − 1`, `delta_e ≥ 0`, `upscale_factor: int`.
  Fail-closed by `str(item.path)`; never copied between items.
- Veil/plate paint: **W1 only**. W2 MUST NOT add paint code.

## Phases

0. **Pre-flight (each worker):** `AGENTS.md` (app) + `skills/sli-ui-toolkit-docs-first/SKILL.md`
   (docs-first, painter pipeline, no QSS) + `skills/imgsli-devtools/SKILL.md` (tracer pick for
   runtime verification) + `design.md` + S4 LIGHT svg + own scoped files +
   `BUTTON_API.md` regions/`pixmap` section (W1, copied into cell by supervisor).
   Record base SHA of `int/gallery-light` in DONE.
1. **W1 | W2 in parallel** — 2 clone cells (`agent-clone.sh improve-imgsli <id>`),
   branches `agent/<id>/work`, timebox **M = 120 min**, heartbeats (pre-flight ≤15,
   baseline green ≤30, first scoped edit ≤45, first push ≤60). Every wait slice:
   `agent-spin.sh` + `scripts/worker_progress.sh` + user-visible checkpoint line.
2. **Integration (supervisor):** merge W1 → `int/gallery-light` first, then W2 onto it
   (W2 consumes W1's `refresh_metrics`); claimed-vs-real file reads; INTERFACE grep
   for duplicates; `auto:` count = 0; `python src/devtools/docs_link_graph.py --write-index`
   (new plan doc); registry resync if new files were added.
3. **Close-out:** queue tasks → `done` + archive split; cells removed same turn;
   push `int/gallery-light` to `private`; ONE PR against private `main` from a
   GitHub-wired checkout.

## Verify (per wave + final)

```bash
QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 python3 -m pytest src/tabs/image_gallery/tests tests/contracts -q -p no:cacheprovider
```

Wave gates: veil test (mirror `test_clean_review_parity.py:274` — `QuickLookOverlay.paintEvent
is not TopLevelInWindowOverlay.paintEvent`), card fill/border/rx asserts, geometry
(content 1040×620, chip/close/footer inside), strip buttons carry pixmaps (no `TypeError`
fallback), offscreen re-render: open overlay → deliver fidelity → overlay shows numbers
without reopen (W2 regression test for the race), meta contains `upscale ×N`, brief visible
with metrics. Counts/windows/emits are not correctness — assert content (numbers, thumbs,
plate pixels), not presence.

## Risks / guards

- Painter pipeline owns visuals: no `setStyleSheet` on toolkit widgets (contract).
- App logic stays in app repo; toolkit repo untouched.
- No `reset --hard`, no `stash`; daemon pauses for merges; `MERGE_HEAD`/`UU` never
  survive a turn.
- Store/event guards unchanged (no store shape change; metrics write path untouched).

## Wave W4 — render fidelity (fonts + chrome + data rows)

Single writer `@ql-s4-w4`, base `9954160e`. Recon 2026-09-23 (3 agents) root-caused
9 divergences; supervisor design decisions frozen below (verbatim in worker prompt).

1. **Fonts:** mockup numbers are logical pt, not physical px. Convert every
   `Label(pixel_size=N)` in `ui/quick_look/` to the point path with the mockup
   number as pt (11.5, 9.5, 13, 12, 10, 9) via `UiFont` point support
   (`ui_font(point_size=)` / `setPointSizeF`; verify Label accepts it, else set
   after construction). No `UiScale` change, no settings change.
2. **Scroll frame:** `QScrollArea` default `StyledPanel` paints the bogus box —
   set frameless (`NoFrame`). Mockup has section dividers only.
3. **Dividers:** `Divider` is a button-region dataclass, not a widget
   (`TypeError` on `parent=`, swallowed) — `_div_series/_div_brief/_div_bar`
   never existed at runtime. Replace with a real 1px widget divider (toolkit
   divider widget if one exists, else the file's own painted pattern). No QSS.
4. **Hint:** move `Esc closes · ←→ walk series` to the right end of the button
   bar row (after stretch), out of the left preview column.
5. **Inset caption:** restructure to an overlaid strip — amber text on a dark
   translucent bar pinned to the inset bottom (per svg:53-64), not a VBox label
   above the pixmap. `SOURCE · name · WxH`, elided to inset width.
6. **Prev/next:** 36px circles overlapping the card edge (half-outside, like
   svg:67-70) via absolute positioning (same idiom as `reposition_source_inset`),
   vertically centered glyph, fixed `#23262b`-token color, keep border when
   disabled (flat disabled look is the current paleness).
7. **Meta ×N:** diagnose the live `n==1` first (log `iw,sw` at read site):
   factor by LONG side (portrait-safe), not width-only; explicit same-size text
   when truly 1 (no silent fallback). Test both `factor=4` (exists) and `1`.
8. **Artifacts:** show ALL rows incl. `clean` (mockup shows `clean edges`); map
   `halo` to a horizontal `_BarWidget` like metrics; banding keeps histogram +
   base + caption. Ensure the artifact channel reaches the open overlay
   (diagnose banding-empty: detector clean vs delivery race; fix whichever).
9. **Strip badges:** move `SOURCE/#N/✕` from `Button(text=)` into badge overlay
   (`ButtonRegion(badge=)` or `setBadge`), keep text-under-button only for
   `tie-break pending`/hint; update parity test that asserts `_text`.
10. **Brief:** numeric fallback stays (VLM non-goal, inherited).

## Wave W5 — fit + live ×N (follow-up, live screenshot 2026-09-23)

Single writer `@ql-s4-w5`, base `9cfbc1a3`. Live screenshot after W4 shows:
right-column vertical + horizontal scrollbars (mockup: none, all fits 1040×620),
values clipped (`#2 of`, `plausib…`, `stron…`), `same size as source` for a
5760×4320 item vs a ~1100×432 source, 7 artifact rows (mockup: Banding + Halo).

Frozen decisions:
1. **×N root fix:** W4 long-side ratio still reads ~1 because both images are
   capped to 1024 BEFORE the ratio is taken (capped-long vs capped-long ≈ 1
   always). Compute the factor from PRE-CAP original dimensions (read sizes
   before `_cap_edge`, or from file metadata), keep W4 debug log. Unit test:
   5760×4320 vs 1100×432 → 5. Portrait/landscape mixed pairs included.
2. **Overlay artifact set = mockup set:** Banding + Halo only. W4 show-all
   overflowed the 620px column (7 rows → scrollbar). Full 7-key set stays in
   card dots/tooltip (unchanged); overlay renders the two mockup rows.
3. **No scrollbars, no clipping:** value + subline labels elide to column width;
   paddings keep 296px right column; offscreen test asserts both scrollbars
   hidden with full content (metrics + 2 artifact rows + series + brief).
4. **Arrows:** verify 36px circles overlap the card edge in offscreen geometry
   (grab or geometry assert); fix if regressed.

Verify: `src/tabs/image_gallery/tests + tests/contracts` green + new tests
(xN pre-cap sizes incl. portrait, overlay row set == {banding, halo},
scrollbars hidden, no clipped value text via elide).

## Wave W6 — strip fit + background-close (follow-up, live screenshot)

Single writer `@ql-s4-w6`, base `fbc6490e`. Leftovers from W5 residuals + user report:
1. Strip hint `click thumb = switch preview` sits INSIDE the strip HBox (175px min)
   and forces h-scroll — mockup svg:170 shows it BELOW thumbs. Move out of row.
2. Thumb pitch 4×74px = 314px > 296px column (mockup pitch 76) — fit thumbs/row
   into 296px (smaller thumbs or tighter spacing, keep badge/click/opacity).
3. Overlay closes on click anywhere; must close only via X button (and Esc —
   keep `close_on_escape=True`). Find the background-close path
   (`TopLevelInWindowOverlay` close_on_background / mouse handler) and disable
   for quick look; verify dbl-click/grid tests don't depend on it.

DEFERRED (user, later wave): prev/next paleness — hypothesis: arrows are painted
before the dim veil around the window (z-order), so the veil mutes them. Verify
paint/stack order when taken up.

Verify: strip fits 296px with 4 thumbs + hint below (no h-scroll, scrollbar
hidden test), background click does not close (offscreen mouse test), X + Esc
still close; full `src/tabs/image_gallery/tests + tests/contracts` green.

## Wave W8 — resizable card (user request)

Single writer `@ql-s4-w8`. Card is currently fixed 1040×620 (min=max).
Frozen decisions:
1. Minimum 1040×620, NO maximum — user drag-resizes via a corner handle
   (bottom-right grip, painter-painted, no QSS); preview pane stretches,
   right column stays fixed 296px; existing reposition hooks (nav, inset)
   already run on resize — reuse, verify.
2. Base overlay centering unchanged (slot CENTER); clamp user size to
   parent/window minus margin; persist nothing (session-only size).
3. Update the 1040×620 geometry test to min-size + resize smoke
   (grow → preview grows, column stays 296, no scrollbars, hooks re-run).

Verify: full `src/tabs/image_gallery/tests + tests/contracts` green.

## Wave W9 — full-border resize + nav arrows (user reports)

Single writer `@ql-s4-w9`, base `46459ae4`. Live reports: (1) only the bottom-right
grip grabs — resize must work along the WHOLE border; (2) prev/next still pale.
Frozen decisions:
1. Resize zone: 8px hit strip along all 4 edges + corners (8 directions),
   hover cursors (H/V/diagonal), drag clamps to min 1040×620 and to parent
   minus margin, session-only. Keep the painted corner grip as a visual affordance
   (it stays one of the 8 handles). No QSS; painter/eventFilter idiom as W8.
2. Arrows: diagnose paleness by execution (offscreen grab: glyph/fill/border
   pixel colors vs mockup `#23262b` glyph on surface circle). Supervisor
   hypothesis: veil paints over them (z-order) — verify or refute; fix the real
   cause (stacking / disabled-look-despite-enabled / glyph color / border loss).
   Mockup: solid 36px circles, centered chevron, half-outside card edge.

Verify: drag each edge/corner (synthetic press-move-release) resizes correctly
with clamp+floor; hover cursors set; arrows pixel-assert (glyph dark, border
present when enabled); full `src/tabs/image_gallery/tests + tests/contracts` green.

## Wave W10 — outer resize ring + arrows live (user live reports)

Single writer `@ql-s4-w10`, base `4b2a9723`. Live screenshot findings:
1. Resize grabs work on the INNER card edge only; the OUTER 8px ring (on the
   dim veil, outside the card) does nothing. Cause: hit-testing lives on card
   children, nothing owns the outside ring. Fix: own the outer ring — e.g. an
   invisible 8px grab frame around the card (child of the overlay, behind the
   card) or overlay-level mouse handling in the ring zone; all 8 directions +
   hover cursors as W9; must NOT resurrect background-click close (W6:
   veil clicks do nothing, only the ring drags); must not swallow X/Esc/clicks.
2. Arrows still wrong live: half-outside circles look clipped/pale, glyph
   unreadable (live shot shows a stub, not ‹/›). Diagnose by execution
   (offscreen grab at real geometry incl. the outside half): clipping by
   parent/viewport? glyph font/size? ring paint under veil? Fix real cause;
   mockup: solid 36px, centered chevron, half-outside edge.

Verify: synthetic drags starting OUTSIDE the card (veil ring) resize; veil
click (not drag) still does nothing; arrows grab-assert (full 36px visible,
dark centered glyph, ring present); full suites green.

## Claimed-vs-real close-out



Verify: extended `test_quick_look_parity.py` (pt sizes applied, frameless scroll,
dividers exist, hint in bar row, inset overlay strip, arrows overlap card edge,
×1 text, clean rows visible, halo bar, badge overlay); full
`src/tabs/image_gallery/tests + tests/contracts` green.


Supervisor reads each claimed file at cited line in the worker clone, re-runs the named
suites on the merged tree, greps INTERFACE symbols for duplicates/divergence.

## Progress log

- 2026-09-23: plan written, queue tasks `gallery-ql-s4-w1/w2` filed as `todo`.
- 2026-09-23: W2 DONE — `3089ab82` pushed, 1917 passed (fidelity refresh + set-source re-run).
- 2026-09-23: W1 attempts 1–2 died with zero edits (supervisor prompt bug: required doc
  outside the jail). W1 narrowed to S (quick_look.py + helpers.py + parity tests);
  strip pixmap + histogram base split to `gallery-ql-s4-w3` (todo). Attempt 3 live.
- 2026-09-23: W1 DONE — `f80baf39` (veil, plate, nav, crop gate, refresh_metrics,
  11 new tests). Merged W1 → int/gallery-light (`8b266a8d`), then W2 (`256b5e58`).
  Merged-tree suites: 1929 passed. Pushed to private; rides PR #87 (open).
  Remaining: `gallery-ql-s4-w3` (strip thumbs, banding base) + tab.py Find-Action
  set-source path (noted by W2, out of scope).

## Catalog update

N/A (app-repo plan; internal-docs `catalog.yaml` covers internal-docs `docs/**` only).
DOC_INDEX regenerated via `docs_link_graph.py --write-index` after merge.
