from dataclasses import dataclass

from prellm import levels, report
from prellm.formats import OUTPUT_EXTENSIONS, InputKind, OutputFormat
from prellm.html.pipeline import html_to_html, html_to_markdown
from prellm.image.ocr import ocr_to_markdown
from prellm.image.raster import RasterResult, convert_raster, image_size
from prellm.image.svg import minify_svg, rasterize_svg
from prellm.levels import Detail


@dataclass(frozen=True)
class Converted:
    data: bytes
    source_tokens: int
    output_tokens: int
    notices: tuple[str, ...]
    extension: str


def convert(data: bytes, kind: InputKind, fmt: OutputFormat, detail: Detail) -> Converted:
    source_tokens = _source_tokens(data, kind)
    match (kind, fmt):
        case (InputKind.HTML, OutputFormat.MD):
            result = html_to_markdown(data, levels.markdown_settings(detail))
            return _text(result.text, source_tokens, result.notices, OUTPUT_EXTENSIONS[fmt])
        case (InputKind.HTML, OutputFormat.HTML):
            result = html_to_html(data, levels.html_settings(detail))
            return _text(result.text, source_tokens, result.notices, OUTPUT_EXTENSIONS[fmt])
        case (InputKind.RASTER, OutputFormat.IMAGE):
            return _image(convert_raster(data, levels.raster_settings(detail)), source_tokens)
        case (InputKind.RASTER, OutputFormat.MD):
            text, frames_dropped = ocr_to_markdown(data, levels.ocr_settings(detail))
            return _text(
                text, source_tokens, _frame_notices(frames_dropped), OUTPUT_EXTENSIONS[fmt]
            )
        case (InputKind.SVG, OutputFormat.IMAGE):
            return _image(rasterize_svg(data, levels.raster_settings(detail)), source_tokens)
        case (InputKind.SVG, OutputFormat.SVG):
            return _text(
                minify_svg(data, levels.svg_settings(detail)),
                source_tokens,
                (),
                OUTPUT_EXTENSIONS[fmt],
            )
    raise ValueError(f"{fmt} output is not supported for {kind} input")


def _source_tokens(data: bytes, kind: InputKind) -> int:
    if kind is InputKind.RASTER:
        return report.image_tokens(*image_size(data))
    return report.text_tokens(len(data))


def _text(text: str, source_tokens: int, notices: tuple[str, ...], extension: str) -> Converted:
    return Converted(
        data=text.encode("utf-8"),
        source_tokens=source_tokens,
        output_tokens=report.text_tokens(len(text)),
        notices=notices,
        extension=extension,
    )


def _image(result: RasterResult, source_tokens: int) -> Converted:
    return Converted(
        data=result.data,
        source_tokens=source_tokens,
        output_tokens=report.image_tokens(result.width, result.height),
        notices=_frame_notices(result.frames_dropped),
        extension=result.extension,
    )


def _frame_notices(frames_dropped: int) -> tuple[str, ...]:
    if frames_dropped == 0:
        return ()
    return (f"kept only the first frame; dropped {frames_dropped} more",)
