from enum import StrEnum
from pathlib import Path


class InputKind(StrEnum):
    HTML = "html"
    RASTER = "raster image"
    SVG = "svg"


class OutputFormat(StrEnum):
    MD = "md"
    HTML = "html"
    IMAGE = "image"
    SVG = "svg"


INPUT_EXTENSIONS = {
    ".html": InputKind.HTML,
    ".htm": InputKind.HTML,
    ".png": InputKind.RASTER,
    ".jpg": InputKind.RASTER,
    ".jpeg": InputKind.RASTER,
    ".gif": InputKind.RASTER,
    ".tif": InputKind.RASTER,
    ".tiff": InputKind.RASTER,
    ".svg": InputKind.SVG,
}

# The first format listed for each kind is its default.
ALLOWED_FORMATS = {
    InputKind.HTML: (OutputFormat.MD, OutputFormat.HTML),
    InputKind.RASTER: (OutputFormat.IMAGE, OutputFormat.MD),
    InputKind.SVG: (OutputFormat.IMAGE, OutputFormat.SVG),
}

OUTPUT_EXTENSIONS = {
    OutputFormat.MD: ".md",
    OutputFormat.HTML: ".html",
    OutputFormat.IMAGE: ".webp",
    OutputFormat.SVG: ".svg",
}


def input_kind(path: Path) -> InputKind | None:
    return INPUT_EXTENSIONS.get(path.suffix.lower())


def default_format(kind: InputKind) -> OutputFormat:
    return ALLOWED_FORMATS[kind][0]
