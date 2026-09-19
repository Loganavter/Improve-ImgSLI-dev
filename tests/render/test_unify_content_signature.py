"""Content-signature probe for the vanish hunt (ic-right-image-vanish-2026-09-19).

The accurate-branch unify exit can hand out a valid-sized but pixel-blank
member that every downstream health check (size/uid/residency/coverage)
passes. `unify_content_signature` is the tripwire; these tests pin its
contract plus the accurate branch staying non-blank on healthy inputs.
"""

from PIL import Image

from engine.store.pixel_ops.unify import unify_content_signature, unify_pair


def test_signature_none():
    assert unify_content_signature(None) == "None"


def test_signature_solid_reports_nonzero():
    img = Image.new("RGB", (8, 6), (10, 20, 30))
    sig = unify_content_signature(img)
    assert "8x6" in sig
    assert "zero5=False" in sig


def test_signature_black_reports_zero5():
    img = Image.new("RGB", (8, 6), (0, 0, 0))
    assert "zero5=True" in unify_content_signature(img)


def test_accurate_branch_pair_stays_nonblank():
    img1 = Image.new("RGBA", (64, 48), (200, 30, 30, 255))
    img2 = Image.new("RGBA", (128, 96), (30, 200, 30, 255))
    u1, u2 = unify_pair(img1, img2, "LANCZOS")
    assert u1 is not None and u2 is not None
    assert "zero5=False" in unify_content_signature(u1)
    assert "zero5=False" in unify_content_signature(u2)
