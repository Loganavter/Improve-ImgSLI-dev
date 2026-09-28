# Plan: MC parametric crop — context-menu crop like IC, no baked re-decode

Status: `Approved for fleet` — baked-crop approach (per-slot re-decode, cache key dimension, reload orchestration) superseded 2026-09-29 after engine survey.
Area: `src/tabs/multi_compare/` (menu, render passes, export), `src/engine/store/crop_window.py` (new)
Related: `src/tabs/image_compare/ui/context_menu.py:105` (IC Crop entry, the parity target), `src/tabs/image_compare/canvas/texture_parts/crop_clip.py` (IC render-time clip concept), `docs/dev/plan_shared_pixel_registry.md` (full-frame decodes share best under key `None`)
Skills: `skills/imgsli-devtools/SKILL.md` (contracts `./launcher.sh test tests/contracts -q`, `QT_QPA_PLATFORM=offscreen pytest`)

> **Reader note (fleet supervisor + lane workers).** An earlier wave baked crop at decode (per-slot re-decode + bool cache keys). It was reverted: every surveyed engine does crop as a **param applied at sampling**, never as a re-decode. This plan implements that. Decode stays full-frame forever; the menu flips a param; render clips; export bakes. Toggle cost: one `canvas.update()`, zero decodes.

## 1. Goal and non-goals

**Goal:** per-slot Crop toggle in the multi-compare canvas context menu, mirroring IC (`crop_override` True/False/None-Auto + global `auto_crop_black_borders` fallback, checkable entry, instant apply). Same file in two slots may carry different crop states with correct pixels everywhere (live, preview, export).

**Non-goals / do not touch:**
- IC crop path (works, no-bake already) — read-only reference
- Gallery QuickLook coarse path, video-export direct `from_path` decodes
- `TiledPixelStore` memmap format, shared-pixel registry, funnel (full-frame in → full-frame out; crop never reaches them)
- Pyramid builds (pyramid stays full-frame superset; crop clips reads, never rebuilds)
- Disk thumbnails, GPU textures (per-widget RHI)

## 2. Research summary (verified 2026-09-29, do not re-research)

| Engine | Crop model | Evidence |
|---|---|---|
| GEGL (GIMP core) | `gegl:crop width= height=` — op node **properties** in a processing graph; UI edits props, engine renders on demand | gegl.org ops, `gegl-chain` property syntax `op prop=value` |
| darktable | crop **module params** (`cx,cy,cw,ch` + aspect); pipe applies at render; module deliberately **late** so full frame stays available (e.g. retouch) | `src/iop/crop.c`, manual: "full uncropped image will be shown" in focus |
| Lightroom | **parametric recipe** (crop rectangle as text in catalog); engine renders original through recipe; virtual copies = one source, N param sets | catalog/XMP parametric editing docs |
| IC (ours) | decode full-frame no-bake; `crop_clip` at render | `image_decode.py:141` (`crop_service=None`), `canvas/texture_parts/crop_clip.py` |

Verdict: decode-once-full-frame + crop-as-sampling-param. The per-slot state is a tiny param (IC parity: `crop_override` bool|None on the slot; box resolved via the shared `CropService` helper). No re-decode, no eviction orchestration, no cache-key dimension, undo-safe (flag restore is always consistent — pixels were never baked).

## 3. Frozen seam (all lanes implement/consume verbatim)

```python
# tabs/multi_compare/use_cases/crop.py  (lane STATE produces, RENDER+EXPORT consume read-only)
def effective_crop_box(controller, slot) -> tuple[int, int, int, int] | None:
    """(left, top, right, bottom) in FULL-FRAME source px, or None = no crop.
    override True -> service box (or None if the service reports no box);
    override False -> None; override None -> global setting, then service box.
    Never raises (any failure -> None = show full frame)."""
```

Render contract (lane RENDER): **every** per-slot read box MUST be intersected with the effective box when not None; the slot's reported size is the cropped size; LOD scale is computed against the cropped size; out-of-range/empty intersection renders gap (fail-closed, never neighbor bytes). Engine helper (lane ENGINE):

```python
# engine/store/crop_window.py  (pure, no Qt, no tabs — engine seal applies)
def intersect_box(box, crop) -> tuple[int,int,int,int] | None
def crop_view_size(full_size, crop) -> tuple[int,int]
```

Export contract (lane EXPORT): composition bakes the effective box (crop-then-compose, PIL/`store.crop` level, never a second decode).

## 4. Lanes (disjoint files, max 4 writers)

| Lane | Files (exclusive) | Scope |
|---|---|---|
| `mc-crop-engine` (S) | NEW `src/engine/store/crop_window.py`, NEW `tests/render/test_crop_window.py` | Pure box math + identity tests (distinct payloads, empty-intersection gap, full-frame passthrough). Touches NO existing file. |
| `mc-crop-state` (S) | `src/tabs/multi_compare/context_menu.py`, `src/tabs/multi_compare/controller.py` (one method `set_slot_crop_override` only), `src/tabs/multi_compare/resources/i18n/{en,ru}/multi_compare.json` (`context.crop` only), NEW `src/tabs/multi_compare/use_cases/crop.py`, MC menu/reducer tests | Checkable Crop entry (IC parity: label via `_tr("context.crop")`, `Icon.SCISSORS`), execute → controller method → `SetCropOverride` dispatch (base branch already has model field + action + reducer) + `canvas.update()` — NO evict, NO reload, NO decode. |
| `mc-crop-render` (M) | `src/tabs/multi_compare/scene/passes/base_images.py`, `.../residency.py`, `.../slot_resources.py`, `src/tabs/multi_compare/ui/canvas_widget.py`, `src/tabs/multi_compare/canvas/interaction.py` | Per-slot effective box via the §3 helper; clip every read box; cropped sizes into grid/LOD; gap on empty intersection. Render tests with distinct-content images (color-per-index harness, never counts-only). |
| `mc-crop-export` (S) | `src/tabs/multi_compare/use_cases/export.py`, export tests | Bake effective box at composition from cached FULL stores; cropped and uncropped slots sharing one path export their own pixels. |

Base: `origin/feat/mc-crop-context-menu @ c30b183e` (slot field + action + reducer already in). Workers: `git fetch origin && git checkout -B agent/<task-id>/work origin/feat/mc-crop-context-menu`, record base SHA in prompt. Integration: supervisor merges lanes sequentially into `int/mc-crop`, re-runs lane suites + contracts per merge.

## 5. Acceptance

- Menu: same-path slots with different overrides show different pixels live (distinct-color harness); toggle is instant (no `from_path` in log between toggle and repaint); checkmark reflects effective state; Auto follows the global setting flip.
- Render: zoom/LOD/grid correct on cropped slots (no stretch, no neighbor bytes); empty intersection = gap.
- Export: mixed-override composition matches live pixels per slot.
- Suites per lane (offscreen): lane tests + `tests/contracts` + `tests/render` + MC tab tests. Registry tests must stay green (decodes stay full-frame: funnel log shows `crop_service` from MC loads unchanged in shape — full-frame spills shared across tabs as before).
- `file_meta --write-registry` resync if any tracked file crosses/returns over limits; doc-link graph test green (`python src/devtools/docs_link_graph.py --write-index` after adding docs).

## 6. Risks

1. LOD/grid keyed on full size elsewhere (labels, dividers, focus-dim passes read sizes too) — lane RENDER audits every `pixel_source_size`/size consumer for its touched paths; untouched passes keep full-frame behavior (only cropped slots change).
2. Box staleness on file replace — `CropService` owns invalidation (existing); a stale box clips wrong but never crashes (clamped to frame; empty → gap).
3. Same-path slots across TABS (IC full vs MC cropped) — unchanged: funnel registry already keys by box; MC cache is per-controller.
4. Undo restores the flag only — always consistent (nothing baked). Self-heals by construction.
