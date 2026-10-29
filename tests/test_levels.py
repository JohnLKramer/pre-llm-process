import pytest

from prellm import levels
from prellm.levels import Detail, ImageMode

ORDER = [Detail.MINIMAL, Detail.LOW, Detail.MEDIUM, Detail.HIGH]


@pytest.mark.parametrize(
    ("detail", "max_edge", "quality"),
    [
        (Detail.MINIMAL, 640, 60),
        (Detail.LOW, 1024, 75),
        (Detail.MEDIUM, 1568, 85),
        (Detail.HIGH, None, 90),
    ],
)
def test_raster_settings_match_spec(detail: Detail, max_edge: int | None, quality: int) -> None:
    settings = levels.raster_settings(detail)
    assert (settings.max_edge, settings.quality) == (max_edge, quality)


def test_every_level_has_settings_for_every_pipeline() -> None:
    for detail in Detail:
        levels.raster_settings(detail)
        levels.ocr_settings(detail)
        levels.svg_settings(detail)
        levels.markdown_settings(detail)
        levels.html_settings(detail)


def test_ocr_confidence_decreases_as_detail_increases() -> None:
    confidences = [levels.ocr_settings(d).min_confidence for d in ORDER]
    assert confidences == [80, 60, 40, 0]


def test_markdown_keeps_whole_page_only_at_high() -> None:
    assert [levels.markdown_settings(d).main_content_only for d in ORDER] == [
        True,
        True,
        True,
        False,
    ]


def test_markdown_image_modes() -> None:
    assert [levels.markdown_settings(d).images for d in ORDER] == [
        ImageMode.DROP,
        ImageMode.ALT,
        ImageMode.REF,
        ImageMode.REF,
    ]


def test_html_attributes_only_grow_with_detail() -> None:
    kept = [levels.html_settings(d).kept_attributes for d in ORDER]
    assert kept[0] == frozenset()
    for lower, higher in zip(kept, kept[1:], strict=False):
        assert lower <= higher


def test_detail_parses_from_cli_value() -> None:
    assert Detail("medium") is Detail.MEDIUM
