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

## Claimed-vs-real close-out

Supervisor reads each claimed file at cited line in the worker clone, re-runs the named
suites on the merged tree, greps INTERFACE symbols for duplicates/divergence.

## Progress log

- 2026-09-23: plan written, queue tasks `gallery-ql-s4-w1/w2` filed as `todo`.
- 2026-09-23: W2 DONE — `3089ab82` pushed, 1917 passed (fidelity refresh + set-source re-run).
- 2026-09-23: W1 attempts 1–2 died with zero edits (supervisor prompt bug: required doc
  outside the jail). W1 narrowed to S (quick_look.py + helpers.py + parity tests);
  strip pixmap + histogram base split to `gallery-ql-s4-w3` (todo). Attempt 3 live.

## Catalog update

N/A (app-repo plan; internal-docs `catalog.yaml` covers internal-docs `docs/**` only).
DOC_INDEX regenerated via `docs_link_graph.py --write-index` after merge.
