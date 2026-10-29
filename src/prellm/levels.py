from dataclasses import dataclass
from enum import StrEnum


class Detail(StrEnum):
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ImageMode(StrEnum):
    DROP = "drop"
    ALT = "alt"
    REF = "ref"


@dataclass(frozen=True)
class RasterSettings:
    max_edge: int | None
    quality: int


@dataclass(frozen=True)
class OcrSettings:
    min_confidence: int
    upscale: int


@dataclass(frozen=True)
class SvgSettings:
    decimals: int | None


@dataclass(frozen=True)
class MarkdownSettings:
    main_content_only: bool
    keep_link_urls: bool
    images: ImageMode


@dataclass(frozen=True)
class HtmlSettings:
    collapse_chrome: bool
    collapse_junk: bool
    structural_only: bool
    flatten_wrappers: bool
    images: ImageMode
    kept_attributes: frozenset[str]


_MEDIUM_ATTRIBUTES = frozenset(
    {"href", "src", "alt", "colspan", "rowspan", "type", "name", "placeholder", "value", "for"}
)

_RASTER = {
    Detail.MINIMAL: RasterSettings(max_edge=640, quality=60),
    Detail.LOW: RasterSettings(max_edge=1024, quality=75),
    Detail.MEDIUM: RasterSettings(max_edge=1568, quality=85),
    Detail.HIGH: RasterSettings(max_edge=None, quality=90),
}

_OCR = {
    Detail.MINIMAL: OcrSettings(min_confidence=80, upscale=1),
    Detail.LOW: OcrSettings(min_confidence=60, upscale=1),
    Detail.MEDIUM: OcrSettings(min_confidence=40, upscale=2),
    Detail.HIGH: OcrSettings(min_confidence=0, upscale=2),
}

_SVG = {
    Detail.MINIMAL: SvgSettings(decimals=0),
    Detail.LOW: SvgSettings(decimals=1),
    Detail.MEDIUM: SvgSettings(decimals=2),
    Detail.HIGH: SvgSettings(decimals=None),
}

_MARKDOWN = {
    Detail.MINIMAL: MarkdownSettings(
        main_content_only=True, keep_link_urls=False, images=ImageMode.DROP
    ),
    Detail.LOW: MarkdownSettings(
        main_content_only=True, keep_link_urls=False, images=ImageMode.ALT
    ),
    Detail.MEDIUM: MarkdownSettings(
        main_content_only=True, keep_link_urls=True, images=ImageMode.REF
    ),
    Detail.HIGH: MarkdownSettings(
        main_content_only=False, keep_link_urls=True, images=ImageMode.REF
    ),
}

_HTML = {
    Detail.MINIMAL: HtmlSettings(
        collapse_chrome=True,
        collapse_junk=True,
        structural_only=True,
        flatten_wrappers=True,
        images=ImageMode.ALT,
        kept_attributes=frozenset(),
    ),
    Detail.LOW: HtmlSettings(
        collapse_chrome=True,
        collapse_junk=True,
        structural_only=False,
        flatten_wrappers=True,
        images=ImageMode.ALT,
        kept_attributes=frozenset({"href"}),
    ),
    Detail.MEDIUM: HtmlSettings(
        collapse_chrome=False,
        collapse_junk=True,
        structural_only=False,
        flatten_wrappers=True,
        images=ImageMode.REF,
        kept_attributes=_MEDIUM_ATTRIBUTES,
    ),
    Detail.HIGH: HtmlSettings(
        collapse_chrome=False,
        collapse_junk=False,
        structural_only=False,
        flatten_wrappers=False,
        images=ImageMode.REF,
        kept_attributes=_MEDIUM_ATTRIBUTES | {"id", "class", "role", "aria-label"},
    ),
}


def raster_settings(detail: Detail) -> RasterSettings:
    return _RASTER[detail]


def ocr_settings(detail: Detail) -> OcrSettings:
    return _OCR[detail]


def svg_settings(detail: Detail) -> SvgSettings:
    return _SVG[detail]


def markdown_settings(detail: Detail) -> MarkdownSettings:
    return _MARKDOWN[detail]


def html_settings(detail: Detail) -> HtmlSettings:
    return _HTML[detail]
