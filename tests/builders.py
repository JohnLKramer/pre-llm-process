import io
from pathlib import Path

from PIL import Image, ImageDraw

FIXTURES = Path(__file__).parent / "fixtures"


def screenshot_png(width: int = 1170, height: int = 2532) -> bytes:
    """A phone-screenshot-like PNG: a gradient with bars of 'text'."""
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(0, height, 4):
        shade = 255 - (y * 80 // height)
        draw.rectangle([0, y, width, y + 4], fill=(shade, shade, 255))
    for y in range(100, height - 100, 60):
        right = max(61, width - 60 - (y % 300))
        draw.rectangle([60, y, right, y + 24], fill=(20, 20, 20))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def jpeg_with_exif() -> bytes:
    exif = Image.Exif()
    exif[0x010F] = "Canon"
    out = io.BytesIO()
    Image.new("RGB", (800, 600), "orange").save(out, "JPEG", exif=exif.tobytes())
    return out.getvalue()


def rotated_jpeg() -> bytes:
    """A 400x200 JPEG, left half red and right half blue, stored with EXIF Orientation 6."""
    image = Image.new("RGB", (400, 200), "red")
    ImageDraw.Draw(image).rectangle([200, 0, 399, 199], fill="blue")
    exif = Image.Exif()
    exif[0x0112] = 6
    out = io.BytesIO()
    image.save(out, "JPEG", exif=exif.tobytes())
    return out.getvalue()


def animated_gif(frames: int = 3) -> bytes:
    images = [Image.new("RGB", (200, 100), color) for color in ("red", "green", "blue")[:frames]]
    out = io.BytesIO()
    images[0].save(out, "GIF", save_all=True, append_images=images[1:], duration=100)
    return out.getvalue()


def multipage_tiff(pages: int = 2) -> bytes:
    images = [Image.new("RGB", (300, 200), color) for color in ("white", "black")[:pages]]
    out = io.BytesIO()
    images[0].save(out, "TIFF", save_all=True, append_images=images[1:])
    return out.getvalue()


def transparent_png() -> bytes:
    out = io.BytesIO()
    Image.new("RGBA", (100, 100), (255, 0, 0, 0)).save(out, "PNG")
    return out.getvalue()
