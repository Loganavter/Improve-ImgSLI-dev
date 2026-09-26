# Plan: S3 clean-review overlay — visual parity with mockup v3 (QuickLook idiom)

Status: `draft` · Date: 2026-09-26 · Owner: @jorj
Base branch: `feat/gallery-reject-removes-card`
Mockup: [design/ui-mockup-v3-clean-review.svg](design/ui-mockup-v3-clean-review.svg)
        (+ `-light` variant). QL reference: `ui/quick_look/overlay_build.py`,
        `ui/quick_look.py:show_for`.

## Goal / non-goals

**Goal:** S3 looks like mockup v3: white rounded card plate centered on the
veil, header + horizontal filmstrip + provenance + bottom action bar —
built with the same idioms QuickLook uses for mockup v4 (plate painter,
section builders, `show_overlay()` sizing).

**Non-goals:**
- toast redesign (post-move toast already exists via ToastManager);
- S3 close policy (`close_on_background/deactivate=True` stays);
- filmstrip virtualization (cap + more-tile stays);
- vertical-scroll debates (mockup: single horizontal strip).

## Gap analysis (screenshot vs mockup vs code)

| # | Mockup v3 | Live S3 now | Cause in code |
|---|---|---|---|
| G1 | White card 900×440 rx12 border `#d7dade`, all sections inside | Title/subtitle/buttons float on gray veil; filmstrip white box inset oddly | `_content = plain QWidget` (transparent), `clean_review.py:141`; min size only 520×360, no `sizeHint` |
| G2 | Horizontal strip: 4× 150×100 thumbs + name + ↩ Restore each, `+29 more` dashed tile | Vertical scroll, one thumb + white void + vertical scrollbar | `_populate` builds per-series vertical rows (`:449-624`); strip direction never horizontalized |
| G3 | Bottom bar on plate: Restore all \| `33 files · 214 MB` centered \| Cancel \| blue primary Move | Same elements, floating on veil | Follows from G1 (no plate) |
| G4 | Header: title 16 bold + 12 muted subtitle + divider rule | Title 14 + caption 11, no divider | `clean_review.py:157-169`; QL has `_RuleWidget` (`overlay_build.py`) |
| G5 | Provenance `from: SERIES…` under strip | Present ✓ | Keep |
| G0 | Overlay fills parent on open | Painted ~nothing (FIXED this turn) | `show_for` lacked `show_overlay()` — fixed + `test_show_for_sizes_overlay_to_parent` |

QL-in-code pattern to copy (`overlay_build.py:112-176`, `:464-475`, `quick_look.py:346-370,848`):
`_CardPlate` (explicit paintEvent, theme-subscribed bg/border rx12, token
chains, zero hardcoded QColor) → `setMinimumSize` + overlay `sizeHint()` →
`show()` + `show_overlay()` + post-show re-pin. Section builders, everything
via `scaled_px`; word-wrap width discipline (W7).

## Phases

**Phase 1 — Card plate.** S3 `_ReviewPlate` mirroring `_CardPlate`
(bg `gallery.card.background`→`surface.list`, border `gallery.card.border`→
`flyout.border`, rx12, theme_changed resubscribe). Move `_content` children
onto the plate; min size ≈ mockup 900×440 via `scaled_px`; overlay
`sizeHint()` like QL `:848`.
Verify: `test_show_for_sizes_overlay_to_parent` + veil pixel test stay
green; offscreen: plate fills centered rect, border pixels present.

**Phase 2 — Header.** Title 16 bold, subtitle 12 muted, divider rule
(reuse QL `_RuleWidget` idiom, no new widget family).
Verify: text asserts in `test_clean_review_parity.py` (extend).

**Phase 3 — Horizontal filmstrip.** Per-series section → horizontal strip:
150×100 cells (`THUMB_WIDTH/HEIGHT_PX` exist), name + ↩ Restore under each,
`+N more` dashed tile, single `Qt.Horizontal` scroll. Keep per-series
Restore + Restore-all wiring untouched (same callbacks).
Verify: cell count/geometry asserts; `test_thumbs_are_toolkit_labels_150x100`
extended to strip direction.

**Phase 4 — Bottom bar on plate.** Move existing bar as-is; keep Move as
surface + `set_background_color(accent)` (toolkit `primary` is deprecated —
`button.py:251`). Center stats label `N files · X MB` (`_total_bytes_for_items`
exists).
Verify: existing S3 tests green unchanged.

**Phase 5 — Theme parity.** Light (mockup) + dark via tokens only; no
hardcoded QColor (contract `test_no_hardcoded_qcolor`), no QSS.
Verify: full gallery suite + contracts on both themes (offscreen palette
fixtures like `_production_dark_palettes`).

## Risks / guards

- `clean_review.py` is 813 lines (limit 500) but carries
  `Audit-Meta: pattern=state-machine size=exempt` — new builders still go
  into small helpers, no new violations (`test_file_size_policy` already
  red on this branch for other files — do not add more).
- `set_actions`-style `deleteLater` churn: filmstrip rebuild keeps the
  existing `removeWidget+deleteLater` cleanup (`:444-451`).
- Claimed-vs-real close-out: layout-dump the open S3
  (`--dump-ui-layout`) + screenshot-compare against the SVG per phase;
  no phase merges without its Verify asserts.

## Progress log

- 2026-09-26: G0 fixed (`show_overlay()` in `show_for` + regression test).
  294/294 gallery tests green. Plan filed.
- 2026-09-26: Phases 1-5 merged (plate, header, strip top-align, footer
  rule, theme asserts). Live screenshot still far from mockup: series
  section boxes, scroll frames, hollow Move button. New phases below.

## Phase 6 — flat strip (drop series boxes)

Live S3 groups thumbs into bordered per-series sections with headers +
`Restore SERIES N` buttons; mockup v3 shows ONE flat borderless strip
(series live only in the provenance line). Remove section containers +
headers; single flat strip over ALL rejected (cap + more-tile + per-thumb
Restore stay). Scroll areas frameless (`NoFrame`), vertical scrollbar off.
Per-series Restore buttons go away (mockup has none; Restore all +
per-thumb Restore remain). No test pins the boxes (provenance SERIES text
stays — different asserts).

## Phase 7 — solid primary Move + bar polish

Mockup Move: solid `#0096FF` fill + white text. Live: hollow light-blue.
Probe variant semantics offscreen (surface + `set_background_color` vs
alternatives); white text via `setForegroundColor`; toolkit Button has NO
bold API — non-bold white is the accepted deviation (note in DONE).
Bar spacing/centering to mockup on the plate.
