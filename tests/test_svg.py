import io
import re

import pytest
from builders import FIXTURES
from lxml import etree
from PIL import Image

from prellm.image.svg import (
    SvgSizeError,
    intrinsic_size,
    minify_svg,
    rasterize_svg,
    round_numbers,
    round_path,
)
from prellm.levels import Detail, raster_settings, svg_settings

INKSCAPE_SVG = (FIXTURES / "inkscape.svg").read_bytes()
NUMBER = re.compile(r"-?\d*\.\d+")


def test_rasterize_uses_intrinsic_size() -> None:
    result = rasterize_svg(INKSCAPE_SVG, raster_settings(Detail.HIGH))
    image = Image.open(io.BytesIO(result.data))
    assert image.format == "PNG"
    assert result.extension == ".png"
    assert image.mode == "RGBA"
    assert image.size == (120, 81)


def test_rasterize_falls_back_to_viewbox() -> None:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 150"><rect width="10" height="10"/></svg>'
    result = rasterize_svg(svg, raster_settings(Detail.HIGH))
    assert (result.width, result.height) == (300, 150)


def test_rasterize_applies_level_resize() -> None:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="1000"><rect width="10" height="10"/></svg>'
    result = rasterize_svg(svg, raster_settings(Detail.MINIMAL))
    assert (result.width, result.height) == (640, 320)


def test_svg_without_size_is_an_error() -> None:
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="100%"><rect width="10" height="10"/></svg>'
    )
    with pytest.raises(SvgSizeError):
        rasterize_svg(svg, raster_settings(Detail.MEDIUM))


@pytest.mark.parametrize("detail", list(Detail))
def test_minify_removes_editor_cruft_at_every_level(detail: Detail) -> None:
    out = minify_svg(INKSCAPE_SVG, svg_settings(detail))
    for cruft in ("inkscape", "sodipodi", "<metadata", "rdf:", "<!--", "empty-layer"):
        assert cruft not in out
    assert "<title>Badge</title>" in out
    assert "<path" in out and "<circle" in out


@pytest.mark.parametrize(
    ("detail", "max_decimals"),
    [(Detail.MINIMAL, 0), (Detail.LOW, 1), (Detail.MEDIUM, 2)],
)
def test_minify_rounds_coordinates(detail: Detail, max_decimals: int) -> None:
    out = minify_svg(INKSCAPE_SVG, svg_settings(detail))
    path = re.search(r' d="([^"]+)"', out)
    assert path is not None
    for number in NUMBER.findall(path.group(1)):
        assert len(number.split(".")[1]) <= max_decimals


def test_minify_high_keeps_coordinates() -> None:
    out = minify_svg(INKSCAPE_SVG, svg_settings(Detail.HIGH))
    assert "10.123456,20.987654" in out


def test_minify_never_rounds_transforms() -> None:
    out = minify_svg(INKSCAPE_SVG, svg_settings(Detail.MINIMAL))
    assert 'transform="rotate(12.5 60 40)"' in out


def test_round_numbers_keeps_adjacent_numbers_apart() -> None:
    assert round_numbers("M1.5.5L10-0.4", 0) == "M2 0L10 0"
    assert round_numbers("M 10.126,-3.004", 2) == "M 10.13,-3"


def test_round_path_keeps_arc_flags_separate() -> None:
    assert round_path("M0 0a1.26 1.26 0 11.5.5", 1) == "M0 0a1.3 1.3 0 1 1 0.5 0.5"


def test_round_path_arc_flags_repeat_per_segment() -> None:
    assert round_path("A1 1 0 1 0 2 2 1 1 0 0 15 5", 0) == "A1 1 0 1 0 2 2 1 1 0 0 1 5 5"


def test_round_path_rounds_non_arc_commands() -> None:
    assert round_path("M1.5.5L10-0.4z", 0) == "M2 0L10 0z"


def test_round_path_rejects_invalid_arc_flag() -> None:
    with pytest.raises(ValueError, match="M0 0a1 1 0 2 1 5 5"):
        round_path("M0 0a1 1 0 2 1 5 5", 1)


def test_minify_rounds_every_coordinate_attribute() -> None:
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10.26 20.74">'
        b'<circle cx="1.26" cy="2.74" r="3.51" transform="rotate(12.345)"/>'
        b'<polygon points="0.26,0.74 5.5,5.5"/></svg>'
    )
    out = minify_svg(svg, svg_settings(Detail.MINIMAL))
    assert 'viewBox="0 0 10 21"' in out
    assert 'cx="1"' in out and 'cy="3"' in out and 'r="4"' in out
    assert 'points="0,1 6,6"' in out
    assert 'transform="rotate(12.345)"' in out


def test_minify_removes_whitespace_but_keeps_text_and_desc() -> None:
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg">\n  <desc> A  desc </desc>\n'
        b"  <text>\n  Hello <tspan> world </tspan> !\n</text>\n  <rect/>\n</svg>"
    )
    out = minify_svg(svg, svg_settings(Detail.HIGH))
    assert "<desc> A  desc </desc>" in out
    assert "<text>\n  Hello <tspan> world </tspan> !\n</text>" in out
    assert "</desc>\n" not in out
    assert "<rect/></svg>" in out


def test_minify_removes_illustrator_and_sketch_cruft() -> None:
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:i="http://ns.adobe.com/AdobeIllustrator/10.0/"'
        b' xmlns:sketch="http://www.bohemiancoding.com/sketch/ns" i:foo="1" sketch:type="x">'
        b'<i:pgf>junk</i:pgf><sketch:meta/><rect sketch:type="y" i:bar="2" width="1"/></svg>'
    )
    out = minify_svg(svg, svg_settings(Detail.HIGH))
    assert out == '<svg xmlns="http://www.w3.org/2000/svg"><rect width="1"/></svg>\n'


def test_minify_removes_nested_empty_groups() -> None:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><g><g></g></g><rect/></svg>'
    out = minify_svg(svg, svg_settings(Detail.HIGH))
    assert "<g" not in out


@pytest.mark.parametrize("view_box", ["0 0 a b", "0 0 0 10", "0 0 10 -5"])
def test_intrinsic_size_rejects_bad_viewbox(view_box: str) -> None:
    root = etree.fromstring(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}"/>'.encode()
    )
    with pytest.raises(SvgSizeError, match="viewBox"):
        intrinsic_size(root)
