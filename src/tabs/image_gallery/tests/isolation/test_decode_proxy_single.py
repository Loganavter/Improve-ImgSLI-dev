"""One decode per item in the Stage-2 proxy pass (owner invariant I2).

``run_proxy_stages_sync`` used to decode a ``full_res_artifacts`` item TWICE at
full resolution: ``proxy_for(own)`` (``PIL.Image.open(...).convert("RGB")`` for
the bounded 1024 proxy) and ``TiledPixelStore.from_path(own)`` (the store the
engine measures the tiled catalog on). The store is the authoritative decode and
is already streamed by the time the proxy is needed, so the bounded proxy is
derived FROM it: one item decode, one authoritative pixel buffer.

The seam the engine must keep: in ``full_res_artifacts`` mode the artifact
records are still measured over the FULL-resolution store (docs/ANALYSIS_BACKENDS.md
§10 W14) — the proxy is only the fidelity/camera input. So this file pins both
halves of the contract:

1. ``item decodes == 1`` (``PIL.Image.open`` + ``TiledPixelStore.from_path``
   counted together, so a backend that falls back from pyvips to PIL cannot hide
   a second decode behind the same word);
2. the pixels and the numbers do not move: the proxy is byte-identical to the
   pre-change ``Image.open(...).convert("RGB")`` path (the fixture is a
   1024-edge image, i.e. ``PROXY_MAX_EDGE``, so no resample algorithm sits
   between the two), and the entry's artifact/camera/fidelity dicts equal the
   pre-change oracles (tiled catalog over its own store; the legacy stage
   functions over the same pixels).

Red-before (measured on the pre-change tree): 2 item decodes
(``Image.open == 1`` + ``from_path == 1``). The source reference keeps its own
per-chunk decode (audit R5, out of scope here): 2 source decodes, asserted below
as an explicit "not touched" number rather than left implicit.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tabs.image_gallery.services.proxy import (
    PROXY_MAX_EDGE,
    clear_proxy_cache,
    proxy_for,
    run_proxy_stages_sync,
)

#: The fixture's longest edge is exactly the proxy bound: no downscale, so the
#: pre-change proxy pixels and the store pixels must be byte-identical.
EDGE = PROXY_MAX_EDGE


@pytest.fixture(autouse=True)
def _stub_learned_seams(monkeypatch):
    """Keep the comparison CPU-cheap and deterministic (pattern: W13 tests).

    LPIPS/DISTS/BRISQUE are a torch forward pass over the SAME proxy pixels on
    both sides of the comparison; stubbing the learned seam changes no local
    number under test (ssim/hf_ratio/delta_e/clipping/halo/chroma, camera
    scalars, tiled severities) and keeps the suite off the model download.
    """
    from tabs.image_gallery.services import quality_models

    monkeypatch.setattr(
        quality_models,
        "pair_metrics",
        lambda *a, **k: {"lpips": 0.31, "dists": 0.22},
    )
    monkeypatch.setattr(quality_models, "nr_metrics", lambda *a, **k: {})


def _paint(path: Path, size: tuple[int, int], seed: int) -> Path:
    """Deterministic structured RGB image (detectors see real content)."""
    import numpy as np
    from PIL import Image

    rng = np.random.default_rng(seed)
    width, height = size
    arr = np.clip(rng.normal(128, 22, (height, width, 3)), 0, 255).astype(np.uint8)
    # 8x8 block structure: the tiled catalog has something to measure.
    ramp = (np.arange(width) % 8)[None, :, None]
    arr = np.clip(arr // 2 + ramp * 12, 0, 255).astype(np.uint8)
    Image.fromarray(arr, "RGB").save(path)
    return path


class _DecodeSpy:
    """Counts the two full-resolution decode entry points, per resolved path."""

    def __init__(self) -> None:
        self.image_opens: dict[str, int] = {}
        self.store_opens: dict[str, int] = {}
        self._patchers: list = []

    def start(self):
        from unittest.mock import patch

        import PIL.Image
        from engine.store.tiled_pixel_store import TiledPixelStore

        real_open = PIL.Image.open
        real_from_path = TiledPixelStore.from_path

        def _key(target) -> str:
            try:
                return str(Path(target).resolve())
            except Exception:
                return "<other>"

        def _counted_open(target, *a, **k):
            self.image_opens[_key(target)] = self.image_opens.get(_key(target), 0) + 1
            return real_open(target, *a, **k)

        def _counted_from_path(path, *a, **k):
            self.store_opens[_key(path)] = self.store_opens.get(_key(path), 0) + 1
            return real_from_path(path, *a, **k)

        self._patchers = [
            patch.object(PIL.Image, "open", _counted_open),
            patch.object(TiledPixelStore, "from_path", staticmethod(_counted_from_path)),
        ]
        for patcher in self._patchers:
            patcher.start()
        return self

    def stop(self) -> None:
        for patcher in self._patchers:
            patcher.stop()
        self._patchers = []

    def image_opens_for(self, path: Path) -> int:
        return self.image_opens.get(str(Path(path).resolve()), 0)

    def store_opens_for(self, path: Path) -> int:
        return self.store_opens.get(str(Path(path).resolve()), 0)

    def decodes_for(self, path: Path) -> int:
        return self.image_opens_for(path) + self.store_opens_for(path)


# -- pre-change oracles (independent: they never call the seam under test) ---


def _pre_change_proxy(path: Path):
    """``_build_proxy`` before this change: one PIL decode, same cap, no resize."""
    from PIL import Image

    with Image.open(path) as im:
        orig = (int(im.size[0]), int(im.size[1]))
        rgb = im.convert("RGB")
        width, height = rgb.size
        longest = max(width, height)
        if longest > PROXY_MAX_EDGE:
            scale = PROXY_MAX_EDGE / longest
            resize = getattr(Image, "Resampling", Image).BILINEAR
            rgb = rgb.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))), resize
            )
        rgb.load()
        return SimpleNamespace(image=rgb, size=orig)


def _tiled_oracle(item: Path, source: Path) -> dict:
    """The pre-change artifacts answer: tiled catalog over full-resolution stores."""
    from engine.store.tiled_pixel_store import TiledPixelStore
    from tabs.image_gallery.services.artifact_tiles import analyze_artifacts_tiled

    item_store = TiledPixelStore.from_path(item)
    source_store = TiledPixelStore.from_path(source)
    try:
        return analyze_artifacts_tiled(item_store, source_image=source_store)
    finally:
        item_store.close()
        source_store.close()


# -- the invariant ---------------------------------------------------------


def test_cold_full_res_item_decodes_once(tmp_path: Path) -> None:
    from tabs.image_gallery.services import camera_metrics, fidelity_metrics

    item = _paint(tmp_path / "item.png", (EDGE, 384), seed=11)
    source = _paint(tmp_path / "source.png", (512, 384), seed=5)
    items = [SimpleNamespace(path=item)]

    # Oracles FIRST: they decode on their own and must not land inside the spy.
    expected_item = _pre_change_proxy(item)
    expected_source = _pre_change_proxy(source)
    expected_artifacts = _tiled_oracle(item, source)
    expected_camera = camera_metrics.measure_camera_from_image(expected_item.image)
    expected_fidelity = fidelity_metrics.compute_fidelity_from_images(
        expected_item.image,
        expected_source.image,
        item_size=expected_item.size,
        source_size=expected_source.size,
    )
    assert expected_camera and expected_fidelity, "fixture must be measurable"

    clear_proxy_cache()
    spy = _DecodeSpy().start()
    try:
        out = run_proxy_stages_sync(
            items,
            source,
            include_camera=True,
            full_res_artifacts=True,
        )
    finally:
        spy.stop()

    # ONE item decode: the store is authoritative, the proxy is derived from it.
    assert spy.decodes_for(item) == 1, (
        f"item decoded {spy.decodes_for(item)}x "
        f"(Image.open={spy.image_opens_for(item)}, "
        f"from_path={spy.store_opens_for(item)})"
    )
    assert spy.image_opens_for(item) == 0, "the item's proxy still opened the file"
    assert spy.store_opens_for(item) == 1
    # R5 is out of scope: the source reference still has its per-chunk proxy +
    # store decode (measured: 2). This cell must not add a THIRD one.
    assert spy.decodes_for(source) <= 2, (
        "the source-reference per-chunk decode (audit R5) is not this cell's "
        f"scope, but it must not grow (measured {spy.decodes_for(source)})"
    )

    entry = out[str(item)]
    assert set(entry) >= {"artifacts", "fidelity", "camera", "analysis"}
    assert len(entry["artifacts"]) == 7
    assert entry["analysis"], "the engine records must ride the entry (W9)"

    # The bounded proxy the pass produced is warm and byte-identical to the
    # pre-change decode, and it is derived at the bound (not the full image).
    proxy = proxy_for(item)
    assert proxy is not None
    assert proxy.size == (EDGE, 384)
    assert proxy.image.size == (EDGE, 384)
    assert proxy.image.mode == "RGB"
    assert proxy.image.tobytes() == expected_item.image.tobytes(), (
        "the store-derived proxy changed pixels vs the pre-change PIL decode"
    )
    assert spy.decodes_for(item) == 1, "reading the proxy back re-decoded the file"

    # The numbers did not move. Artifacts are still the FULL-resolution tiled
    # catalog (W14); camera/fidelity are the legacy stage answers over the same
    # proxy pixels the pre-change path fed them.
    assert entry["artifacts"] == expected_artifacts, (
        f"tiled artifacts moved: {entry['artifacts']} != {expected_artifacts}"
    )
    assert entry["camera"] == expected_camera
    assert entry["fidelity"] == expected_fidelity

    # The records behind the entry carry the same artifact ranks (the read path
    # prefers them, W9) — the full-res measurement is what is recorded.
    rank = {"clean": 0.0, "mild": 1.0, "flagged": 2.0}
    records = {record.axis: record for record in entry["analysis"]}
    for artifact, severity in entry["artifacts"].items():
        axis = getattr(artifact, "value", artifact)
        assert records[axis].raw == rank[str(getattr(severity, "value", severity))], axis


def test_warm_proxy_costs_no_decode(tmp_path: Path) -> None:
    """A warm folder still decodes nothing for the proxy (the cache is reused)."""
    item = _paint(tmp_path / "item.png", (256, 192), seed=21)
    items = [SimpleNamespace(path=item)]

    clear_proxy_cache()
    run_proxy_stages_sync(items, None, full_res_artifacts=True)
    warm_proxy = proxy_for(item)
    assert warm_proxy is not None

    spy = _DecodeSpy().start()
    try:
        out = run_proxy_stages_sync(items, None, full_res_artifacts=True)
        again = proxy_for(item)
    finally:
        spy.stop()

    assert spy.image_opens_for(item) == 0, "a cached proxy was rebuilt from the file"
    assert again is warm_proxy, "the cached proxy must be served as-is"
    # The full-res catalog still owns its per-pass store decode — that is the
    # measurement, not the proxy.
    assert spy.store_opens_for(item) == 1
    assert out[str(item)]["artifacts"] == _tiled_oracle_without_source(item)


def _tiled_oracle_without_source(item: Path) -> dict:
    from engine.store.tiled_pixel_store import TiledPixelStore
    from tabs.image_gallery.services.artifact_tiles import analyze_artifacts_tiled

    store = TiledPixelStore.from_path(item)
    try:
        return analyze_artifacts_tiled(store)
    finally:
        store.close()


def test_proxy_only_mode_keeps_its_single_decode(tmp_path: Path) -> None:
    """``full_res_artifacts=False``: one PIL decode, no store at all."""
    item = _paint(tmp_path / "item.png", (320, 240), seed=31)
    items = [SimpleNamespace(path=item)]

    clear_proxy_cache()
    spy = _DecodeSpy().start()
    try:
        out = run_proxy_stages_sync(items, None, full_res_artifacts=False)
    finally:
        spy.stop()

    assert spy.image_opens_for(item) == 1
    assert spy.store_opens_for(item) == 0
    assert spy.decodes_for(item) == 1
    assert out[str(item)]["artifacts"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
