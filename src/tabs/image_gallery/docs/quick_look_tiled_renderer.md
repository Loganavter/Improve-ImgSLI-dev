# Quick Look tiled renderer (single-source, uncapped live path)

The Quick Look overlay draws its preview on one live GPU surface — the
`QuickLookCanvasWidget` (`QRhiWidget`). Two rendering strategies share that
single widget:

| Strategy | Source | Bound | Role |
|---|---|---|---|
| Raster / cover single-quad (`set_source`) | bounded coarse store | 2048 px edge | pre-first-frame plate + fail-open fallback |
| Tiled single-source (`set_tiled_source`) | full `TiledPixelStore` | **uncapped** | the live image at any resolution |
| Demand pyramid (`note_ql_source`) | canvas-private lazy levels | 4096 px edge | sharp wheel-zoom past 1x / dwell |

The tiled path is **additive**: it takes over only once its source is
registered and the RHI is ready. Until then the raster/cover plate keeps
serving, and any per-tile miss fails open to that plate — never to a
neighbour's pixels. There is no second live surface; the tiled renderer is a
draw strategy on the same `QRhiWidget`, not another widget
(`src/tabs/image_gallery/tests/test_ql_tiled_path_regression.py`).

## Bounds

- **Live tiled path — no source-edge cap.** The canvas exists to show the
  full-resolution image; `_decode_full_store_uncapped`
  (`src/tabs/image_gallery/ui/quick_look/preview_canvas_host.py`) deliberately
  applies no edge limit. `QuickLookTileRenderer.set_source` adopts the whole
  `TiledPixelStore` and registers its tile grid.
- **Transient cover raster — 2048 px cap.** `preview_canvas._DECODE_EDGE_CAP`
  and `preview._PREVIEW_FULL_DECODE_EDGE` both stay at 2048; the first-frame
  cover only needs framebuffer resolution.
- **Canvas-private demand pyramid — 4096 px cap.** `preview_canvas._QL_FULL_EDGE_CAP`
  still bounds the lazily built sharp-zoom levels; this is a separate
  mechanism from the tiled live path.

The tiled path is owned by
`src/tabs/image_gallery/ui/quick_look/tile_renderer.py` and consumes the
shared engine stack — `engine.gpu.array_draw` (W0 seam),
`engine.cache.tile_texture_service`, `engine.cache.draw_plans`,
`engine.gpu.array_resources`, `engine.gpu.mip_cascade`. See
`docs/dev/rendering/tile-rendering-system.md` for the engine-level system.

## Content identity (fail closed)

Correctness for the tiled path is **content identity**, not tile counts,
windows, emits, sizes or timing. The invariant is:

> For every emitted instance, the array layer it samples holds *its own*
> tile's content: `payload(tile i) == content(i)`.

This is enforced by construction and pinned by tests:

- each instance's layer resolves from its own `(row, col)` tile index
  (`_build_instances`); a visible tile with no array slot yet is **skipped**,
  never substituted by a neighbour;
- a hole (unresident tile), an evicted neighbour, or a stale prior generation
  is a gap, never a neighbour's payload — the renderer builds a fresh
  `TileTextureService` in `set_source`, so no stale slot can be sampled;
- zoom / resize / reopen re-resolve the index→layer binding with no
  cross-binding;
- cache/slot keys are `(source_id, tile_index)`-shaped, so no key can collide
  across indices;
- geometry derives solely from `store.size` and the framebuffer size — never
  from the first-arrived tile or upload/arrival order.

Regression tests:
`src/tabs/image_gallery/tests/runtime/test_ql_tile_content_identity.py` uses a
content-aware fake that records the fingerprint of the image uploaded into each
array layer, so a swapped / neighbour / stale binding fails on the actual bound
payload (the plan-shape contracts live next door in
`test_ql_tile_renderer.py`).
