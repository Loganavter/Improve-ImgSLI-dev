# Image Gallery — product & interaction design

Status: `Design` (pre-implementation; UI currently a placeholder — see
[README.md](README.md)). Visual references:
[design/ui-mockup-v2-triage.svg](design/ui-mockup-v2-triage.svg) (main triage
screen), [design/ui-mockup-v3-clean-review.svg](design/ui-mockup-v3-clean-review.svg)
(clean flow), [design/ui-mockup-v4-quicklook.svg](design/ui-mockup-v4-quicklook.svg)
(quick look, fidelity mode).

## Role in the product

Improve ImgSLI is a comparison factory ([DEVELOPMENT_HISTORY](../../../../docs/DEVELOPMENT_HISTORY.md)):
Image Compare answers *"how do these two differ"* — a human question.
Multi-image folders break that workflow: dumping 40 outputs of different
upscalers into compare tabs is garbage work no pair of eyes can survive.

The gallery is the **intake and triage surface** that closes this gap:
*"which of these N files are even worth comparing"*. It is explicitly **not**
a general-purpose photo manager and **not** an abstract "AI gallery": there
are no subject tags, no cat detection, no semantic captioning as a primary
feature. AI appears strictly as a quality arbiter, never as a describer.

Typical session:

1. Drop/open a folder → automatic local triage pass runs.
2. Files cluster into series; each series gets a fidelity-ranked best.
3. User corrects ranks, marks rejects, bulk-moves losers to `_rejected/`.
4. Finalists are dispatched into Image Compare / Multi Compare via
   `events/image_carry.py`.

## Triage pipeline

Two passes, both background (`GenericWorker`, never UI-blocking):

### Pass 1 — local (always, offline, ~ms per file)

Runs on decode alongside `services/thumbnail_cache.py`:

- thumbnail render;
- perceptual hash + small embedding vector → clustering (series = ≥2 members
  whose hash/embedding distance is below threshold);
- content-mode metrics (see below) per file;
- hub detection: smallest-resolution centroid member similar to all others →
  candidate **source** image for the folder.

### Pass 2 — VLM API (optional, targeted)

Never runs over the whole folder. Only:

- **tie-break**: top-2 of a series when local metrics are within epsilon
  (badge `AI tie-break…` on both candidates until resolved);
- **compare briefs** for finalists: one structured difference report per pair,
  cached like `services/ai_client.py` results today.

## Analysis modes

Mode is auto-selected per folder and shown as a chip in the stats strip;
`Set as source` (context menu) overrides hub choice manually.

| Mode | Trigger | Ranking metric | Extra readouts |
|---|---|---|---|
| **Fidelity** (default target case) | source hub found (upscale/export batches) | SSIM vs source (`shared/analysis` — same numbers Image Compare shows) | detail gain (HF ratio, restored↔invented scale), ΔE color shift, banding score, halo/overshoot, upscale factor |
| **Camera** | photographic folder, no source hub | sharpness (Laplacian var) | exposure profile + clipping %, noise estimate, WB shift |
| **Batch-synthetic** | tight embedding cloud, no hub, non-photo | distance to cluster centroid | local artifact flags, aesthetic score as tie-break |

### Artifact catalog (first-class, all modes)

Artifacts are the primary rejection signals for processed/AI images. Each has
a local detector, feeds the card dots and the quick look report:

| Artifact | Detector | Typical culprit |
|---|---|---|
| Banding | comb spikes in gradient histogram (sky/gradients) | upscale, heavy compression |
| Halo / edge overshoot | gradient overshoot ratio at strong edges | oversharpening filters |
| Over-smoothing | HF energy loss vs source ("plastic" regions) | aggressive denoise/ESRGAN variants |
| Invented texture | HF gain uncorrelated with source high-freq | hallucinating upscalers |
| Blocking | 8×8 DCT block-boundary energy | JPEG re-save chains |
| Chroma fringing | channel-edge misalignment | cheap demosaic/scalers |
| Noise amplification | high-freq energy gain concentrated in flat areas | naive sharpeners |

Severity per artifact: `clean / mild / flagged` — flagged contributes a warm/red
quality dot on the card and a row in the quick look report.

## UX states

| State | Screen | Notes |
|---|---|---|
| S0 empty | drop zone (`DragDropOverlay` + `DropZoneLabel`) | single `Open Folder…` action |
| S1 scanning | progressive grid fill from thumbnail cache; spinner `n/N` in toolbar | non-modal; grid settles once, when clustering lands |
| S2 triage | stats strip + series-grouped grid | main state, see v2 mockup |
| S2a review corrections | hover mini-capsule `★ make best · ✕ reject · ⇄ compare`; ContextMenu mirrors it | reject = dim to 38% + strike-through, reversible until Clean |
| S3 clean review | modal overlay listing rejected files with per-item Restore, provenance-by-series line, `Move N to _rejected/` | move-only deletion model, toast Undo 10 s |
| S4 quick look | large preview + fidelity/camera report + series strip | double-click; ←→ walks series; Esc closes |

Manual selection (marquee/Ctrl-click, bottom selection HUD with
`Compare → / Analyze / Find similar`) stays orthogonal to triage mechanics:
selection is about *dispatching*, crown/reject are about *folder quality*.
During the S3 overlay the HUD is suppressed (`FlyoutManager` group).

### Stats strip (S2+)

`40 images · 7 series · 33 redundant` + actions `Keep best`,
`Clean rejected (n)` (live count), `Compare finalists`, plus mode chip
(`FIDELITY MODE · source: …`). Series headers appear only for clusters ≥2;
singles collect under a plain `UNGROUPED` tail.

### Card anatomy

Cover region + name row; rank badge (`★ BEST` accent pill or `#N` gray);
three quality dots (artifact-based per the Artifact catalog above — the three
mode-relevant artifacts, e.g. fidelity: banding/halo/blocking; a `flagged`
severity shows its dot warm/red); rejected =
opacity 0.38 + struck name + ✕ corner badge; unreadable file = error placeholder,
excluded from triage but visible.

### Quick look report (S4)

Left: large preview with **source inset** (fidelity mode) and sharpness-crop
inset; prev/next walk the series. Right: metric bars per mode, artifact rows
with mini-detector visualizations (gradient-histogram comb for banding),
series strip (SOURCE / viewing / pending / rejected thumbs, click to switch),
and — only if pass 2 ran for this pair — a one-line compare brief. Bottom bar:
`Compare →`, `Add to Multi Compare`, `✕ Reject`, `Set as source` (fidelity only).

Keyboard: `←→↑↓` navigate · `Space` reject toggle · `B` make best · `Enter`
compare selected · dbl-click quick look · `Esc` close/back.
Find Action ids: `gallery.keep-best-of-series`, `gallery.clean-rejected`,
`gallery.run-triage`, `gallery.set-as-source`.

## Safety model

- Clean **moves** to `<folder>/_rejected/`; never deletes.
- Toast with `ToastAction("Undo")` (10 s window).
- Review overlay before any move: per-item Restore + restore-whole-series
  provenance grouping (triage can be wrong in bulk).
- API pass is opt-in per folder and never blocks UI; unresolved tie-breaks
  degrade to local ranking silently-but-visibly (pending badge).

## Toolkit rules & patterns (mandatory reading before any UI code)

Full sources: [AGENTS.md «Toolkit widgets and reusable UI»](../../../../AGENTS.md),
[UI_TOOLKIT_LIBRARY.md](../../../../docs/dev/UI_TOOLKIT_LIBRARY.md),
skill `.cursor/skills/sli-ui-toolkit-docs-first/SKILL.md`, structure rules in
[CODE_PATTERNS.md](../../../../docs/dev/CODE_PATTERNS.md). Short version for
this tab:

**Docs first.** Before writing or changing any widget — read the toolkit docs,
not its source: sibling `../sli-ui-toolkit` `docs/user/API_CATALOG.md`,
`BUTTON_API.md`, `FLYOUT_SYSTEM.md`, `INPUTS_API.md`, `OVERLAYS_API.md`,
and `docs/dev/DESIGN_LANGUAGE.md`. Stock Qt is the fallback only when the
toolkit genuinely has no equivalent — never the starting point.

**Which toolkit copy is authoritative.** Check `requirements-gui.txt`: while
the `-e ../sli-ui-toolkit` line is present, the sibling checkout is installed
editable — its source/docs are live and authoritative; edits there take
effect. Without that line treat the toolkit as a pinned external dependency:
don't edit the sibling expecting effect and don't trust its source over the
released API.

**Hard rules** (enforced by contract tests, not conventions):

- No stock layout/QSS styling of toolkit widgets: **no `setStyleSheet`,
  no raw `QFormLayout`/`QVBoxLayout` construction blocks** — the painter
  pipeline owns all visual output. Colors/fonts only through theme tokens
  (`themes.json` + `ThemeManager`); never hand-roll colors.
- Import from the public surface: `from sli_ui_toolkit.widgets import …`
  (thin shims and internals are not API).
- Keep app-specific logic out of the toolkit; reusable-only API belongs in
  the toolkit repo (external `Loganavter/sli-ui-toolkit`).
- Do not silently remove legacy-compat imports (`shared_toolkit/*`) unless
  the whole tree is migrated (AGENTS.md rule).

**Structure patterns** ([CODE_PATTERNS.md](../../../../docs/dev/CODE_PATTERNS.md)):

- *Thin owner + `use_cases/`*: `widget.py` keeps state, wiring, and
  Qt-name-required delegators; bodies live as plain functions taking the
  owner (`ui/` or `use_cases/` home per owner type). Keep method names stable
  when splitting — tests reach into them.
- *Who owns the state*: concerns with their own lifecycle (selection HUD,
  marquee gesture, triage worker coordination) become small collaborator
  objects parameterizable across hosts (precedent: `tabs/_shared/save_flow.py`);
  widget-glue whose state lives on the owner stays a use_cases function.
  A split that needs a grab-bag module ("helpers", "misc") is a wrong split —
  see "when not to split" (a virtualized grid state-machine like
  `session_picker/recent/items_view.py` stays whole).
- *No implied lookups*: dependencies are passed explicitly, never fished via
  `getattr`/registry string-dispatch (contract-tested).
- File-size policy: >500-line files need `Audit-Meta:` marker
  ([FILE_SIZE_POLICY.md](../../../../docs/dev/FILE_SIZE_POLICY.md)); run
  `python src/devtools/file_meta.py --write-registry` after size-changing edits.

Verification loop after any UI change here:
`./launcher.sh test tests/contracts -q` +
`env QT_QPA_PLATFORM=offscreen pytest -q src/tabs/image_gallery/tests`.

## Toolkit mapping

| Element | Widget |
|---|---|
| Card | `Button(regions=[cover pixmap image_fill="cover", text rows], split=VerticalSplit)`, `setBadge` for rank/AI |
| Hover capsule | `IconActionFlyout` pattern, `FlyoutManager` group `gallery_card` |
| Selection HUD | `BaseFlyout` glass capsule pinned bottom-center, group `gallery_selection` |
| Marquee | `MarqueeBandOverlay` + `MarqueeBandGesture` (session_picker precedent) |
| Context menu | `ContextMenu` + `popup_context_menu_for_anchor` |
| Quick look / clean review | `TopLevelInWindowOverlay` |
| Empty state | `DragDropOverlay` + `DropZoneLabel` |
| Toolbar | `Button(variant="surface")`, `CustomLineEdit`, `ScrollableComboBox`, icon-pair `toggle=True` view switch |
| Workers/progress | `GenericWorker` (+ `ToastProgressBar` where a toast fits) |
| Toasts | `ToastManager` + `ToastAction("Undo")` |
| Theming/i18n/scale | painter-pipeline tokens only (no ad-hoc QSS), `{{tr:image_gallery.*}}` ×4 locales |

## Implementation anchors

Existing modules this design builds on (no new infrastructure required for
pass 1): `services/thumbnail_cache.py`, `services/folder_scanner.py`,
`services/filtering.py` (re-purposed to metric/tag predicates),
`shared/analysis/*` (SSIM/PSNR/diff reuse — parity with Image Compare numbers
is a product requirement, not a nice-to-have), `events/image_carry.py`
(dispatch into workspace tabs), `plugins/settings` contribution path for
API settings (`ui/settings_ai.py` returns with stage 2).

Phasing:

1. **Stage 1 — browse & dispatch** (no AI): S0–S2 flat grid, marquee,
   selection HUD, carry hand-off. Card = cover Button region.
2. **Stage 2 — local triage**: clustering, camera/fidelity modes, stats strip,
   crown/reject/clean flow, quick look with local report.
3. **Stage 3 — API layer**: tie-breaks, compare briefs, semantic search field
   becomes functional (filter by VLM tags stored alongside analysis cache).
4. **Stage 4 — hooks for future workspaces**: video-compare intake follows the
   same triage contract.

## Light-theme contrast norm

WCAG ratios (`ratio = (L1 + 0.05) / (L2 + 0.05)`) over the W1 light palette
(`src/resources/themes.json`), enforced by
`tests/test_light_contrast.py` against the live file (no duplicated hexes):

| Pair | Threshold | Current |
|---|---|---|
| card (`gallery.card.background`) vs `Window` | ≥ 1.5 | 1.57 |
| card vs `surface.background` | ≥ 1.5 | 1.57 |
| hover (`gallery.card.hover`) vs card | ≥ 1.3 | 1.37 |
| `separator.color` vs card / `Window` / `surface.background` | ≥ 3.0 | 4.95 / 3.15 / 3.15 |
| stats bg (`gallery.stats.background`) vs card | ≥ 3.0 | 3.45 |
| header / footer / stats texts vs their backgrounds | ≥ 4.5 | 6.3–11.7 / 4.78 (stats) |

**Substrate-darker-than-cards principle.** Cards are white (`#ffffff`); the
substrate they sit on (`Window` / `surface.background`) must be darker, or
cards dissolve into the background (the old `#f5f5f5`-on-`#f5f5f5` 1:1 bug).

**Why `Window` is `#cecece`.** White cards need a gray substrate to read as
objects at all. The card border (`button.dialog.default.border`, alpha hairline)
is decoration only — fill contrast carries the separation, so the substrate
stays mid-gray rather than near-white.

**Visual gate.** Before any PR to `main` touching gallery tokens: run the app
with `./launcher.sh run --ui-inspector` and confirm cards, hover, stats strip,
separators, and quick look still separate in BOTH themes
(`tests/test_light_dark_flip.py` covers the flip headlessly, but it cannot
judge beauty — eyes still required).
