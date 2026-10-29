import io
from dataclasses import dataclass

from PIL import Image, ImageOps, ImageStat

from prellm.levels import RasterSettings

_EXIF_ORIENTATION = 0x0112
# Orientations that swap width and height on display.
_TRANSPOSING_ORIENTATIONS = (5, 6, 7, 8)


@dataclass(frozen=True)
class RasterResult:
    data: bytes
    width: int
    height: int
    frames_dropped: int
    extension: str


def open_first_frame(data: bytes) -> tuple[Image.Image, int]:
    """Return the first frame as an RGB or RGBA image, and how many frames were dropped."""
    with Image.open(io.BytesIO(data)) as source:
        frame_count = getattr(source, "n_frames", 1)
        source.seek(0)
        upright = ImageOps.exif_transpose(source) or source
        mode = "RGBA" if _has_alpha(upright) else "RGB"
        frame = upright.convert(mode)
    frame.info.clear()
    return frame, frame_count - 1


def convert_raster(data: bytes, settings: RasterSettings) -> RasterResult:
    frame, frames_dropped = open_first_frame(data)
    frame = _shrink(frame, settings.max_edge)
    out = io.BytesIO()
    if _has_transparent_pixel(frame):
        frame.save(out, "PNG", optimize=True)
        extension = ".png"
    else:
        frame.convert("RGB").save(out, "JPEG", quality=settings.quality, optimize=True)
        extension = ".jpg"
    return RasterResult(
        data=out.getvalue(),
        width=frame.width,
        height=frame.height,
        frames_dropped=frames_dropped,
        extension=extension,
    )


def image_size(data: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(data)) as source:
        width, height = source.size
        if source.getexif().get(_EXIF_ORIENTATION) in _TRANSPOSING_ORIENTATIONS:
            return height, width
        return width, height


def _has_alpha(image: Image.Image) -> bool:
    return image.mode in ("RGBA", "LA", "PA") or (
        image.mode == "P" and "transparency" in image.info
    )


def _has_transparent_pixel(image: Image.Image) -> bool:
    if image.mode != "RGBA":
        return False
    lowest_alpha, _ = ImageStat.Stat(image.getchannel("A")).extrema[0]
    return lowest_alpha < 255


def _shrink(image: Image.Image, max_edge: int | None) -> Image.Image:
    longest = max(image.size)
    if max_edge is None or longest <= max_edge:
        return image
    scale = max_edge / longest
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)
