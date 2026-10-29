import pytest
from builders import FIXTURES, animated_gif, screenshot_png

from prellm.convert import convert
from prellm.formats import InputKind, OutputFormat
from prellm.levels import Detail


def test_html_to_markdown_estimates_tokens() -> None:
    data = (FIXTURES / "article.html").read_bytes()
    converted = convert(data, InputKind.HTML, OutputFormat.MD, Detail.MEDIUM)
    assert converted.data.startswith(b"# The Best Trail Running Shoes")
    assert converted.source_tokens == -(-len(data) // 4)
    assert converted.output_tokens < converted.source_tokens


def test_raster_estimates_use_pixels() -> None:
    converted = convert(screenshot_png(), InputKind.RASTER, OutputFormat.IMAGE, Detail.MEDIUM)
    assert converted.source_tokens == 3950
    assert converted.output_tokens == 1516
    assert converted.extension == ".jpg"


def test_text_outputs_carry_their_format_extension() -> None:
    html = (FIXTURES / "article.html").read_bytes()
    svg = (FIXTURES / "inkscape.svg").read_bytes()
    assert convert(html, InputKind.HTML, OutputFormat.MD, Detail.LOW).extension == ".md"
    assert convert(html, InputKind.HTML, OutputFormat.HTML, Detail.LOW).extension == ".html"
    assert convert(svg, InputKind.SVG, OutputFormat.SVG, Detail.LOW).extension == ".svg"
    assert convert(svg, InputKind.SVG, OutputFormat.IMAGE, Detail.LOW).extension == ".png"


def test_dropped_frames_become_a_notice() -> None:
    converted = convert(animated_gif(3), InputKind.RASTER, OutputFormat.IMAGE, Detail.LOW)
    assert converted.notices == ("kept only the first frame; dropped 2 more",)


def test_svg_minify() -> None:
    data = (FIXTURES / "inkscape.svg").read_bytes()
    converted = convert(data, InputKind.SVG, OutputFormat.SVG, Detail.LOW)
    assert b"inkscape" not in converted.data


def test_unsupported_combination_raises() -> None:
    with pytest.raises(ValueError, match="not supported"):
        convert(b"", InputKind.HTML, OutputFormat.IMAGE, Detail.LOW)
