"""Degenerate-upload tripwire (ic-right-image-vanish-2026-09-19).

Uploading a null/zero-area image marks a layer resident while leaving
zeros behind — healthy counts, white side. `is_degenerate_upload_image`
is the pure detector; `upload_tile_to_array` warns on it without
changing behavior.
"""

from PIL import Image
from PySide6.QtGui import QImage

from engine.gpu.array_resources import (
    is_blank_upload_image,
    is_degenerate_upload_image,
)


def test_none_is_degenerate():
    assert is_degenerate_upload_image(None) is True


def test_null_qimage_is_degenerate():
    assert is_degenerate_upload_image(QImage()) is True


def test_zero_area_qimage_is_degenerate():
    img = QImage(10, 10, QImage.Format.Format_RGBA8888)
    assert is_degenerate_upload_image(img) is False
    assert is_degenerate_upload_image(QImage(0, 0, QImage.Format.Format_RGBA8888)) is True


def test_healthy_pil_is_not_degenerate():
    assert is_degenerate_upload_image(Image.new("RGBA", (4, 4))) is False


def test_blank_transparent_qimage_is_blank():
    img = QImage(10, 10, QImage.Format.Format_RGBA8888)
    img.fill(0x00000000)
    assert is_blank_upload_image(img) is True


def test_red_qimage_is_not_blank():
    img = QImage(10, 10, QImage.Format.Format_RGBA8888)
    img.fill(0xFFFF0000)
    assert is_blank_upload_image(img) is False


def test_null_qimage_is_not_blank_double_count():
    # Degenerate owns the null case; blank stays quiet on unreadables.
    assert is_blank_upload_image(QImage()) is False
