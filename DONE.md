STATUS: done
PR: "none"

TESTS:
- `QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 python3 -m pytest src/tabs/image_gallery/tests/runtime/test_analysis_payload_budget.py -q -p no:cacheprovider -o addopts=""` → **10 passed** (the new pinned seams).
- `QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/contracts/test_gallery_judge_cache_identity.py src/tabs/image_gallery/tests/runtime -q -p no:cacheprovider -o addopts=""` → **629 passed** (baseline before this branch: 619 passed).
- `QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 python3 -m pytest src/tabs/image_gallery/tests -q -p no:cacheprovider -o addopts=""` → **2168 passed, 2 skipped** (whole gallery tab dir, both commits applied).
- `QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 python3 -m pytest src/tabs/image_gallery/tests/contracts -q -p no:cacheprovider -o addopts=""` → **14 passed**; `tests/contracts/test_analysis_no_model_literals.py test_analysis_substrate_contracts.py test_gallery_ai_domain_read.py` → **66 passed**.
- `tests/contracts/test_file_size_policy.py` → 2 passed, 1 failed: **pre-existing** (`src/core/control/server.py` 610 lines, `src/tabs/image_gallery/use_cases/profile_ai.py` 506 lines — both untouched by this branch, no markers). request.py 497 and proxy.py 500 lines stay under the 500 gate; ai_analysis.py/triage_run.py keep their existing Audit-Meta.
- `python scripts/check_comment_citations.py` → 297 findings, all pre-existing; none in a line this branch added.

INTERFACE:
- `ai_client.request.WireImage(mime, data_b64, edge, source_bytes, wire_bytes)` — the wire copy of one image.
- `ai_client.request.encode_wire_image(image_bytes, mime, *, max_edge=None, prefer_jpeg=True) -> WireImage` — THE per-card encoder (ceiling + mime + admission gate).
- `ai_client.request.encode_wire_path(image_path, *, max_edge=None, prefer_jpeg=True) -> WireImage` — read once + encode.
- `ai_client.request.resolve_wire_max_edge(explicit=None) -> int` — user setting (`vlm_max_edge_px`) else `decode_policy.VLM_DEFAULT_MAX_EDGE_PX`; `0` = originals.
- `ai_client.request.build_request(..., wire=None, max_edge=None)` / `build_request_from_bytes(..., wire=None, max_edge=None)` — one payload builder; `wire` reuses an encode across k draws.
- `ai_client.request.DEFAULT_WIRE_ENCODE_SLOTS = 2`, `WIRE_ENCODE_SLOTS_ENV = "IMGSLI_GALLERY_WIRE_ENCODE_SLOTS"`, `wire_encode_gate_stats() -> {slots, active, peak}`, `reset_wire_encode_gate()`.
- `services.proxy.run_proxy_stages_sync(items, source_path, cancel=None, *, include_camera, full_res_artifacts)` — `cancel` is the per-item generation check; yields the GIL every 2 items.
- `use_cases.ai_analysis._hydrate_ai_cache(owner, items, *, ctx=None, budget_ms=None) -> int` — bounded GUI batch + continuation (`_HYDRATE_BUDGET_MS = 8.0`).
- `services.vlm._encode_image(path, *, max_edge=None, prefer_jpeg=False)` keeps its `(mime, b64)` contract but now delegates to `encode_wire_image` (no second suffix table / cap rule).

SELF-REVIEW:
Re-read after writing: `request.py` encode axis (decode→thumbnail→JPEG q85→b64, fail-open to original bytes, `len(data) >= len(raw)` keeps the original, `edge` = the edge actually sent), the gate (`_ensure` sizes from env once; `slot()` never holds the lock across `acquire`; no nested acquisition anywhere), `analyze_image_sync` (wire encoded once before the draw loop; a read/encode failure falls back to the per-draw path and the transport reports the error, same as before), `proxy.run_proxy_stages_sync` (yield at every 2nd item, cancel checked at the same boundary, returns the partial path-keyed dict; `proxy_pass._schedule_proxy` owns the `_is_current_folder_gen` closure, so `services/proxy` stays Qt-free and owner-free), `_hydrate_ai_cache` (batch never empty-loops: index 0 always runs; continuation re-checks `_folder_gen`; without a QCoreApplication it finishes synchronously), `_apply_ai_phase` (only the redundant full-card refresh is dropped; `set_activity` still refreshes the phase TTL, so the pulse TTL semantics are unchanged).
Identity check: `services/ai_cache._IDENTITY_FIELDS` / `analysis_cache_identity` untouched — model, base_url, mode, profile, effort, k/temperature/seed, prompt schema. The wire edge is deliberately NOT part of it (task constraint): the same settings keep the same scorecard key, so no cache is invalidated; the model only receives a smaller copy of the same image. Prompt text, response schema and parser untouched (`prompt.py`/`parse.py`/`transport.py` unmodified). Consequence stated honestly: for a user who left the edge at its default, a NEW analysis now shows the model a 1024-px copy instead of a full-resolution one (that is what the existing "Image downscale (max edge)" setting always meant; it simply never reached this path); already-cached scorecards are served as before because the identity is unchanged.
Out-of-scope edit, declared: `src/tabs/image_gallery/tests/test_pipeline_scheduler.py` — three `run_proxy_stages_sync` fakes now accept `cancel=None`, because that file pins the seam whose signature this task added (without it the two scheduling tests time out on a TypeError inside the chunk worker). No other file outside the declared scope was touched.
Debug finding (recorded, not fixed): `services/clustering.cluster_items` unions any pair whose HSV embedding distance is `<= 0.25` regardless of dHash. Two `Image.effect_noise` gray images sit exactly at that line, so `tests/test_series_override.py::test_override_survives_recluster` is RNG-state dependent: it passes alone and failed only because my first fixture consumed Pillow's global noise RNG. I made my fixture use `random.Random(7).randbytes` instead of `effect_noise` — the suite is green now, but the underlying rule is a latent flake in `cluster_items`, not in my code.

SUMMARY:
- Dominant cost BEFORE: per card, the payload was the FULL-RESOLUTION file copied three times (`read_bytes` → `base64` 22.8 ms → `json.dumps` 34.4 ms on a 12.98 MB PNG, ~57 ms of GIL-held copying per draw × 3 draws ≈ 170 ms per card), built by an unbounded number of pool threads — up to 12 cards × k=3 draws could occupy every one of the 4-8 gallery threads, so a wheel notch's visible-thumbnail worker had no thread to run on (measured: 21.4 s vs 6.6 s idle for 40 notches). Secondary: a 50-item Stage-2 chunk with no yield/cancel, the settle AI-cache hydrate in one GUI-thread turn, and a full grid selection sweep on every repeated `waiting` phase emit.
- Dominant cost AFTER: one gated decode+resize+JPEG per card (≈130 ms, at most `DEFAULT_WIRE_ENCODE_SLOTS`=2 threads inside it), then 3 × (b64 0.5 ms + json 0.7 ms) of a 363 KB body — the multi-MB GIL copies are gone (36× smaller wire: 12.98 MB → 363 KB, edge 1024 JPEG), Stage-2 yields every 2 items and stops on a generation change, and the hydrate runs in 8 ms GUI batches.
- Visuals: nothing about the card/dot/pill/quick-look rendering changed; the only data change is the image the model receives. OFFSCREEN-PROVEN only — the 1.3× scroll ratio needs the live proof below.

RED-BEFORE (verbatim, on commit 28ad0ca48 = tests only):
```
10 failed in 2.25s
test_the_per_card_payload_is_capped_and_smaller_than_the_source   (AttributeError: reset_wire_encode_gate)
test_the_wire_edge_follows_the_user_setting                       (AttributeError)
test_the_wire_edge_actually_used_reaches_the_trace                (AttributeError)
test_the_k_draws_encode_the_wire_image_once                       (AttributeError)
test_the_encode_gate_bounds_concurrent_payload_builders           (AttributeError)
test_the_encode_gate_is_configurable                              (AttributeError)
test_a_stage2_chunk_stops_early_on_a_generation_bump              (TypeError: unexpected keyword argument 'cancel')
test_a_stage2_chunk_yields_the_gil_between_items                  (TypeError)
test_the_proxy_scheduler_hands_each_chunk_a_generation_cancel     (IndexError: the seam passes no cancel)
test_the_settle_hydrate_is_time_sliced                            (TypeError: unexpected keyword argument 'budget_ms')
```
and the substantive measurement of the same tree (not just the missing names):
```
BEFORE: source_bytes=9292143 wire_mime=data:image/png wire_edge=2400 wire_bytes=9292143
AFTER : source_bytes=12975375 data:image/jpeg wire_edge=1024 wire_bytes=363156 build_ms=128.7
AFTER : wire encodes for 1 card x 3 draws = 1
```
(2400×1800 incompressible PNG; the file size differs between the two runs because the fixtures differ — both are full-resolution noise; the point is `wire == source` before, `1024-px JPEG` after.)

LIVE-PROOF WANTED (the 1.3× scroll ratio must be measured by the supervisor; it cannot be measured in a clone — the app does not boot here):
```
Prep:   private display only (NEVER :0):  Xvfb :NN -screen 0 1400x1000x24 &
        DISPLAY=:NN LIBGL_ALWAYS_SOFTWARE=1 ./launcher.sh run --debug   (AI trace on)
        Image Gallery tab, open the 36-image series folder, AI enabled, sample_count=3.
Idle pass (t_idle): wait until no card shows an activity pill (all analyses done, no
        Stage-2 pass running), scroll to the top, then 40 notches:
          for i in $(seq 40); do
            mcp: ui_wheel {dx: 0, dy: -120, times: 8}      # 8 wheel steps per notch
            sleep 0.15
          done
        record wall time and the maximum GUI-loop gap (tracer frame-gap / qt_liveness probe).
Busy pass (t_busy): press Analyze on the folder; as soon as cards show "analyzing"/"waiting",
        run the SAME 40-notch loop (same start position); record wall time + max gap.
Ratio:  t_busy / t_idle  -> target <= 1.3   (owner baseline BEFORE: 21.4 s / 6.6 s = 3.24;
        GUI gaps were 288-514 ms; target max gap below ~100 ms)
Log checks (~/.local/share/ImproveImgSLI/log.txt, AI debug):
        - one `wire image mime=jpeg edge=1024 source_bytes=<MB> wire_bytes=<~0.4 MB>` per card
          (plus `analyze wire ready ...`), and `analyze sampling k=3 (cost=3x image calls)`
        - `build_request ... wire_edge=1024 ... b64_chars=~5e5` and `POST ... body_bytes=~4.8e5`
          (was ~1.1e7-1.7e7)
        - with IMGSLI_GALLERY_WIRE_ENCODE_SLOTS unset the gate registers 2 slots
          (`wire_encode_gate_stats()` shows peak 2 under 12 queued cards)
Stage-2: open a large folder (>=50 images) and switch folders mid-pass; the log must show
        `proxy batch: stopped at item N (generation moved)` instead of a full 50-item pass.
Visual: covers, quality dots, AI/ALG markers, activity pills and the quick-look report look
        exactly as before; only the uploaded image is smaller.
```
