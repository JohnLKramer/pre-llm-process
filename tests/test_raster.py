import io

import pytest
from builders import (
    animated_gif,
    jpeg_with_exif,
    multipage_tiff,
    opaque_rgba_png,
    rotated_jpeg,
    screenshot_png,
    transparent_png,
)
from PIL import Image

from prellm.image.raster import convert_raster, image_size
from prellm.levels import Detail, RasterSettings, raster_settings


def decode(data: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(data))
    image.load()
    return image


@pytest.mark.parametrize(
    ("detail", "expected_size"),
    [
        (Detail.MINIMAL, (296, 640)),
        (Detail.LOW, (473, 1024)),
        (Detail.MEDIUM, (725, 1568)),
        (Detail.HIGH, (1170, 2532)),
    ],
)
def test_screenshot_longest_edge_follows_level(
    detail: Detail, expected_size: tuple[int, int]
) -> None:
    result = convert_raster(screenshot_png(), raster_settings(detail))
    image = decode(result.data)
    assert image.format == "JPEG"
    assert result.extension == ".jpg"
    assert image.size == expected_size == (result.width, result.height)


def test_small_images_are_never_upscaled() -> None:
    result = convert_raster(screenshot_png(200, 100), raster_settings(Detail.MINIMAL))
    assert (result.width, result.height) == (200, 100)


@pytest.mark.parametrize("detail", list(Detail))
def test_metadata_is_stripped_at_every_level(detail: Detail) -> None:
    result = convert_raster(jpeg_with_exif(), raster_settings(detail))
    image = decode(result.data)
    assert image.format == "JPEG"
    assert not image.getexif()
    assert "icc_profile" not in image.info
    assert "exif" not in image.info


def test_exif_orientation_is_applied_before_stripping() -> None:
    result = convert_raster(rotated_jpeg(), raster_settings(Detail.HIGH))
    image = decode(result.data)
    assert image.size == (200, 400)
    rgb = image.convert("RGB")
    assert rgb.getpixel((0, 0)) == pytest.approx((255, 0, 0), abs=20)
    assert rgb.getpixel((0, 399)) == pytest.approx((0, 0, 255), abs=20)
    assert not image.getexif()


def test_image_size_reports_display_orientation() -> None:
    assert image_size(rotated_jpeg()) == (200, 400)


def test_animated_gif_keeps_first_frame_and_reports_dropped() -> None:
    result = convert_raster(animated_gif(frames=3), raster_settings(Detail.MEDIUM))
    image = decode(result.data)
    assert result.frames_dropped == 2
    assert getattr(image, "n_frames", 1) == 1
    assert image.convert("RGB").getpixel((0, 0)) == pytest.approx((254, 0, 0), abs=3)


def test_multipage_tiff_keeps_first_page() -> None:
    result = convert_raster(multipage_tiff(pages=2), raster_settings(Detail.MEDIUM))
    assert result.frames_dropped == 1
    assert decode(result.data).convert("RGB").getpixel((0, 0)) == pytest.approx(
        (255, 255, 255), abs=3
    )


def test_transparency_survives_as_png() -> None:
    result = convert_raster(transparent_png(), RasterSettings(max_edge=None, quality=90))
    image = decode(result.data)
    assert image.format == "PNG"
    assert result.extension == ".png"
    assert image.mode == "RGBA"
    assert image.getpixel((0, 0))[3] == 0


def test_fully_opaque_alpha_becomes_rgb_jpeg() -> None:
    result = convert_raster(opaque_rgba_png(), RasterSettings(max_edge=None, quality=90))
    image = decode(result.data)
    assert image.format == "JPEG"
    assert result.extension == ".jpg"
    assert image.mode == "RGB"


def test_higher_quality_produces_larger_file() -> None:
    png = screenshot_png(800, 800)
    low = convert_raster(png, RasterSettings(max_edge=None, quality=60))
    high = convert_raster(png, RasterSettings(max_edge=None, quality=90))
    assert len(low.data) < len(high.data)


def test_corrupt_image_raises() -> None:
    with pytest.raises(OSError):
        convert_raster(b"not an image", raster_settings(Detail.MEDIUM))


def test_image_size_reads_dimensions() -> None:
    assert image_size(screenshot_png(300, 500)) == (300, 500)
