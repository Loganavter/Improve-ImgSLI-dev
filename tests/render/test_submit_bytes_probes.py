"""Submit-bytes probes (ic-right-image-vanish-2026-09-19).

`unpack_packed_split` / `unpack_instance_layer2` read back the exact
bytes handed to the GPU so the submitted split and instance layers can
be compared against scene/plan values. Pure helpers, no GPU needed.
"""

import struct

from tabs.image_compare.canvas.rhi_renderer.use_cases.draw import (
    _INSTANCE_LAYER2_OFFSET,
    _INSTANCE_STRIDE,
    _PACKED_SPLIT_OFFSET,
    unpack_instance_layer2,
    unpack_packed_split,
)


def _fake_uniforms(split: float) -> bytes:
    buf = bytearray(192)
    struct.pack_into("<f", buf, _PACKED_SPLIT_OFFSET, split)
    return bytes(buf)


def _fake_instances(layer2_values) -> bytes:
    blob = bytearray()
    for l2 in layer2_values:
        inst = bytearray(_INSTANCE_STRIDE)
        struct.pack_into("<i", inst, _INSTANCE_LAYER2_OFFSET, l2)
        blob += inst
    return bytes(blob)


def test_unpack_packed_split_roundtrip():
    assert unpack_packed_split(_fake_uniforms(0.5)) == 0.5
    assert unpack_packed_split(_fake_uniforms(0.0)) == 0.0
    assert unpack_packed_split(b"short") is None
    assert unpack_packed_split(None) is None


def test_unpack_instance_layer2_roundtrip():
    blob = _fake_instances([79, 66, 54])
    assert unpack_instance_layer2(blob, 0) == 79
    assert unpack_instance_layer2(blob, 1) == 66
    assert unpack_instance_layer2(blob, 2) == 54
    assert unpack_instance_layer2(blob, 3) is None
    assert unpack_instance_layer2(blob, -1) is None
    assert unpack_instance_layer2(None, 0) is None
