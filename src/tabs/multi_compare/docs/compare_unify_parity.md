# Compare-Unify Parity (Multi Compare)

What the frozen loading seam owns vs what stays tab-local in multi_compare.
Seam: `src/tabs/_shared/loading_pipeline.py` (frozen, consume-only).

## Moved to the seam (do not re-implement here)

- File-identity key `(normpath, mtime_ns, size)`, boxless by construction:
  `src/tabs/_shared/loading_pipeline.py:74-95`. Identical to the tab
  `cache_key_for_path` (`src/tabs/multi_compare/pipeline/cache.py:40-59`);
  single-flight keys delegate to one construction site.
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

- Layout tree (`LeafNode`/`SplitNode`, weights, drop targets, divider
  resize on tree paths): tab `docs/ARCHITECTURE.md` layout model. The seam
  never sees the tree — it resolves payloads per slot id only.
- Gap rendering (split gaps as solid-color GPU quads from
  `ResolvedComposition.gaps`): tab `docs/ARCHITECTURE.md` rendering
  section. Seam-side, a missing tier is just `None`; drawing the gap is
  the tab renderer/composition plan's job.
- `NoteSlotPixels` (revision bump only, STORE replace-only) and the
  composition build from `sources={slot_id: pixels}`: tab
  `docs/ARCHITECTURE.md` state section. Slot-indexed dispatch payloads
  (`sizes_for_slots` at `src/tabs/multi_compare/pipeline/cache.py:299-322`)
  stay tab-side; the seam carries the `slot_id` through but never dispatches.
- `resolve` / `resolve_slot_source` (pixel-first, then preview, else
  imageless `None`): `src/tabs/multi_compare/pipeline/cache.py:209-221`,
  `:278-287`. Render paths keep using these, never blocking decode.
- Cache lifecycle (evict/close/release, generation counter):
  `src/tabs/multi_compare/pipeline/cache.py:240-254`, `:104-110`.

## Parity tests

`src/tabs/multi_compare/tests/compare_unify/test_loading_seam_parity.py`:
key shape/boxless, MC key-constructor agreement, delegation + cache-through,
fail-closed misses, `resolve` gap agreement, per-slot distinct-content
identity, sparse/evicted/stale-after-fresh gaps, per-slot async routing,
`{slot_id: size}` index keys, picking/pyramid fail-open.
