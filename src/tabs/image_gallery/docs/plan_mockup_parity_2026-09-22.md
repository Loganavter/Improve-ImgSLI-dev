# Plan: Image Gallery — parity close-out (S2/S3/S4)

Status: `draft` · Date: 2026-09-22 · Owner: @jorj
Base branch: `docs/plan-gallery-parity-2026-09-22`
Tracked in internal-docs: `docs/backlog/queue.yaml` (tasks gallery-parity-A..D).

Closes the gaps between the implementation and the three design mockups
([design/ui-mockup-v2-triage.svg](design/ui-mockup-v2-triage.svg),
[design/ui-mockup-v3-clean-review.svg](design/ui-mockup-v3-clean-review.svg),
[design/ui-mockup-v4-quicklook.svg](design/ui-mockup-v4-quicklook.svg)),
per the 2026-09-22 four-agent audit + supervisor code verification.
Prior audit status: [design_parity_audit.md](design_parity_audit.md).
Product spec: [design.md](design.md).

## Goal / non-goals

**Goal:** close all verified divergences — 10 P0 functional bugs + visual
parity + theme-token hygiene. Tab already exists (Stage 1–2 live); this is a
parity close-out, not a rewrite.

**Non-goals:**
- list view (S2-8 stays a grid-only stub);
- real `Find similar` (HUD button stays a stub);
- unified S1–S4 state machine refactor;
- VLM Pass-2 expansion (briefs/tie-break stay as-is);
- promoting `success/warning/danger` tokens into `sli-ui-toolkit`
  (separate toolkit task, separate repo).

**Decision (confirmed):** quality dots stay **artifact-based** (design.md
artifact catalog → warm/red dots). The mockup footer legend
(`sharpness/exposure/noise`) is wrong — fix the legend in design.md/mockup
annotation, not the code.

## P0 bugs (verified by supervisor against code)

| # | Bug | Evidence |
|---|---|---|
| P0-1 | `_series_of` does not read `series` (only `_triage_series`/`triage_series`/`_series`) → `keep_best`/`compare_finalists` degrade when owner=controller | `use_cases/triage.py:125`, `controller.py:529`, workaround `tests/runtime/test_gallery_truth.py:186`. **Wave A must verify `_owner_for_triage()` return value first.** |
| P0-2 | `Clean rejected (n)` not live: `set_rejected_count` only from `widget.py:827` + `quick_look.py:377`; `toggle_reject → _refresh_owner_grid` path silent | `use_cases/triage.py:267,390` |
| P0-3 | Fidelity metrics dead: **no writer** for `metrics["ssim"/"hf_ratio"/"delta_e"/"upscale_factor"]` — S4 always "not measured"; `shared/analysis.calculate_ssim` never called from gallery | grep `src/` → readers only |
| P0-4 | Dual-bar marker inverted: `0.5 + hf*0.5` → hf=+0.18 gives 0.59 (invented side); mockup wants 0.41 (restored side) | `ui/quick_look/bars.py:168,190` |
| P0-5 | "Add to Multi Compare" clobbered: `_on_multi` adds to selection then emits → `on_quick_compare` overwrites `selected_paths = {path}` | `ui/quick_look.py:330-348` → `ui/quick_look_hooks.py:150` |
| P0-6 | "Set as source" does not switch mode (only relabels chip with old mode) | `ui/quick_look.py:387-413` |
| P0-7 | `toolbar.py` uses `Qt` without import (NameError swallowed by try/except) | `ui/toolbar.py:12` vs `:233,242` |
| P0-8 | Banding "· sky region" fake (no region analysis; leftover from prior audit fix) | `ui/quick_look/artifacts.py:113-114` |
| P0-9 | Banding histogram clips spikes: `setFixedHeight(36)` but spikes up to 50 (mockup container 56) | `ui/quick_look/histograms.py:72,110,128` |
| P0-10 | Dim-veil 0.45: `TopLevelInWindowOverlay` has **no paintEvent** — audit agents disagreed; verify both overlays actually dim; add app-side veil if missing | `sli-ui-toolkit .../overlays/in_window_overlay.py` |

## Visual divergences (from audit, file:line)

**S2:** view-toggle active fill-chip vs border (`ui/toolbar.py:293`);
AI tie-break as in-thumbnail pill not top-right badge (`ui/card/visuals.py`);
series header uppercase + letter-spacing + token instead of raw `#9a9a9a`
(`ui/grid_view.py:478,507`); rank badge text `#dfdfdf` not white
(`ui/card/visuals.py:176`); 6 raw-hex sites (`ui/card.py:213,222`,
`ui/card/hover.py:37,44,59,65`, `ui/card/regions.py:93`); unreadable "!"
size-24 + `#303030` plate (`ui/card/regions.py:62`); hover capsule
tri-color icons ★/✕/⇄ (`ui/card/hover.py` — post size-fix).

**S3:** provenance line **below** filmstrip + `from: ` prefix
(`ui/clean_review.py:159` vs svg:100); horizontal scroll past cap 8
(`ui/clean_review.py:480`); toast `files` not `file(s)`, `success=True`
(green check), no MB suffix (`ui/clean_review.py:685-693`); primary button
comment claims `variant="primary"`, code does surface+accent
(`ui/clean_review.py:204`).

**S4:** meta order `dims · format · size` (`ui/quick_look/helpers.py:500`);
series header `Series 1 · hub` (`helpers.py:546`); mode-chip pill background
(`helpers.py:166`); divider lines (svg:144,174,179); panel min 1040×620
(`helpers.py:155`); green color on metric values; deterministic `vs #2`
brief fallback from local metrics when VLM absent.

## Ownership (4 waves, disjoint, cap 4 writers)

| Wave | Owns files | Scope |
|---|---|---|
| **A triage-core** | `use_cases/triage.py`, `use_cases/triage_ui.py`, `use_cases/carry.py`, `widget.py`, `tests/runtime/test_gallery_truth.py` | P0-1, P0-2; strip Keep best → `keep_best_of_series` (mockup spec `gallery.keep-best-of-series`); live count in `_refresh_owner_grid`; stale "(stub)" docstrings |
| **B fidelity+S4** | `controller.py`, `services/**` (+ new `services/fidelity_metrics.py`), `ui/quick_look.py`, `ui/quick_look/**`, `ui/quick_look_hooks.py`, `icons.py`, `tests/test_quick_look_parity.py` | P0-3,4,5,6,8,9; metric writers via `shared/analysis`; all S4 visual gaps |
| **C s2-visuals** | `ui/card.py`, `ui/card/**`, `ui/grid_view.py`, `ui/toolbar.py`, `ui/stats_strip.py`, `ui/states.py`, `ui/selection_hud.py`, `ui/marquee.py`, `tests/test_card_parity.py`, `tests/test_toolbar_parity.py` | P0-7; all S2 visual gaps; raw-hex → tokens; design.md dots-legend fix |
| **D s3+veil** | `ui/clean_review.py`, `tests/test_clean_review_parity.py` (+ app-side veil helper if verify says so) | all S3 visual gaps; P0-10 veil verify/fix |

### INTERFACE (declare verbatim in every worker prompt)

- `_series_of(owner)` — attribute order `_triage_series, triage_series,
  _series, series` on `owner`, then on `owner.state`. **Wave A only** —
  no second implementation anywhere.
- `item.metrics` fidelity keys (**produces + consumes wave B only**):
  `ssim ∈ [0,1]`, `hf_ratio = hf_out/hf_in − 1` (marker
  `frac = 0.5 − clamp(hf,−1,1)·0.5`, so +0.18 → 0.41 per mockup),
  `delta_e ≥ 0`, `upscale_factor: int`. Identity fail-closed: keys written
  strictly by `item.path`, never copied between items.
- `stats_strip.set_rejected_count(n)` — existing public method, signature
  unchanged; wave A adds a call site only.

## Phases

0. **Pre-flight (each worker):** read `design.md` + 3 SVGs +
   `design_parity_audit.md` + own scoped files. Wave A first verifies
   `_owner_for_triage()`; wave D first verifies overlay veil.
1. **Waves A|B|C|D in parallel** — 4 clone cells
   (`agent-clone.sh improve-imgsli <id>`), branches `agent/<id>/work`,
   timebox **M = 120 min**, heartbeats (pre-flight ≤15, baseline green ≤30,
   first scoped edit ≤45, first push ≤60). Every wait slice: `agent-spin.sh`
   + `scripts/worker_progress.sh` + user-visible checkpoint.
2. **Integration (supervisor):** merge into `int/gallery-parity-2026-09`,
   claimed-vs-real (read files at cited lines — never trust diff alone),
   full suite, grep INTERFACE for duplicates/divergence, `auto:` commits = 0
   before PR.
3. **Close-out:** update `design_parity_audit.md` with a new status section;
   queue tasks → `done` (+ archive via `scripts/queue_archive_split.py`);
   `agent-clone.sh remove <task-id>` same turn; PR opened from a
   GitHub-wired checkout against the **private** remote.

## Verify (per wave + final)

```bash
QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 \
  pytest -q src/tabs/image_gallery/tests tests/contracts -p no:cacheprovider
```

Baseline (must stay green): gallery **102 passed**, contracts
**1768 passed, 66 skipped**.

New regressions (minimum):
- **A:** `keep_best` with controller-owner reads `state.series` → count > 0;
  strip count grows after Space-reject.
- **B:** writers produce the 4 keys; `frac(0.18) ≈ 0.41`; multi-compare
  keeps `|selection| ≥ 2` after two adds; set-source flips chip to FIDELITY.
- **C:** `rg '#9a9a9a' ui/grid_view.py` → 0; toolbar `Qt` import covered by
  parity test.
- **D:** provenance matches `^from:`; toast matches `Moved \d+ files`.

Guards: `test_hover_capsule_flyout_fits_its_buttons` must not regress
(hover capsule size fix from 2026-09-22 stays).

## Risks / guards

- `widget.py` — wave A only; `controller.py` — wave B only (no cross-edits).
- Strip Keep best → `keep_best_of_series` is a **behavior change** (rejects
  rest — it is the mockup spec; palette action already wires it at
  `tab.py:430`).
- Store guards: selection stays plain state fields (no new mutation paths);
  metrics identity fail-closed (no cross-item key copy).
- If the veil fix belongs in `sli-ui-toolkit` → separate clone + separate
  PR, never edited from gallery cells.
- Toolkit rules: no QSS, no stock layouts for toolkit widgets; colors only
  via ThemeManager tokens with hex fallback.

## Claimed-vs-real close-out (supervisor)

Read each claimed file at the cited line; re-run the full gallery+contracts
suite on the merged tree; grep every `INTERFACE:` symbol for a second
implementation; `git log main..HEAD --oneline | grep -c "auto:"` must be 0;
resync registries if touched; remove cells same turn.

## Progress log

- 2026-09-22: plan drafted from 4-agent audit + supervisor verification;
  decisions: dots stay artifacts, orchestration = plan + queue.yaml.
- 2026-09-22 23:15: supervisor baseline green (1870 passed, 66 skipped);
  int/gallery-parity-2026-09 cut; waves A|B|C|D provisioning started.

## Catalog update

On approval (internal-docs): add plan entry to `docs/catalog.yaml`
(`id` == filename slug == frontmatter id, `status: draft`, `tags`,
`relates_to` ≥ this plan + `src/tabs/image_gallery/docs/design.md`), run
`scripts/gen_indexes.py`. Queue tasks A–D live in
`docs/backlog/queue.yaml`.
