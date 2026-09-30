# Compare-Unify Parity (Image Compare)

What the frozen loading seam owns vs what stays tab-local in image_compare.
Seam: `src/tabs/_shared/loading_pipeline.py` (frozen, consume-only).

## Moved to the seam (do not re-implement here)

- File-identity key `(normpath, mtime_ns, size)`, boxless by construction:
  `src/tabs/_shared/loading_pipeline.py:74-95`. Matches the first three
  elements of the tab `_pixel_key` / `_preview_key` boxless shapes
  (`src/tabs/image_compare/pipeline/cache.py:166-179`, `:190-202`).
- Path-variant healing: `src/tabs/_shared/loading_pipeline.py:62-71`.
- Sync demand fills (fail-open to `None`): preview at `:117-144`, full-res
  at `:147-177`. Decode delegates to the shared backends, never local code.
- Preview-first async staging (single-flight on the boxless key + bounded
  full FIFO, max 2 in flight / 64 queued): `:415-547`, `:341-355`,
  `:259-338`, bounds at `:45` and `:50`.
- Pyramid kick hook (fail-open no-op without a coordinator): `:550-572`.
- Display picking (`pick_display_image`, pyramid-gated): re-exported at
  `:31` and `:52-59`; canonical impl at
  `src/engine/cache/display_image_picker.py:21-41`.

## Stays tab-local

- Unify tier (`_unify_key`, `get_unified`/`put_unified`):
  `src/tabs/image_compare/pipeline/cache.py:182-183`, `:662-723`.
  Unification of the two sides is an IC-domain operation, not loading.
- Divider feature (split interaction, geometry, overlay):
  `src/tabs/image_compare/canvas/features/divider/` (see tab
  `docs/ARCHITECTURE.md` canvas-features list). The seam only routes
  payloads per divider side id (0/1); it never lays out the split.
- Eviction/pinning policy (pinned visible entries, LRU + byte budgets,
  eager-drop unify on pixel evict): `src/tabs/image_compare/pipeline/cache.py:298-343`,
  `:593-643`.
- Embedded project-cache lookup stays in the tab `get_or_load` path
  (`:461-511`); the seam fills through `load_pixel_store` only.

## Parity tests

`src/tabs/image_compare/tests/compare_unify/test_loading_seam_parity.py`:
key shape/boxless, IC key-prefix agreement, delegation + cache-through,
fail-closed misses, per-side distinct-content identity, sparse/evicted/
stale-after-fresh gaps, per-side async routing, picking/pyramid fail-open.
