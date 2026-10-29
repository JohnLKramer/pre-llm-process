import pytest
from builders import FIXTURES

from prellm.html.pipeline import html_to_html, html_to_markdown
from prellm.levels import Detail, html_settings, markdown_settings

ARTICLE = (FIXTURES / "article.html").read_bytes()
ORDER = [Detail.MINIMAL, Detail.LOW, Detail.MEDIUM, Detail.HIGH]


def markdown(detail: Detail) -> str:
    return html_to_markdown(ARTICLE, markdown_settings(detail)).text


def html(detail: Detail) -> str:
    return html_to_html(ARTICLE, html_settings(detail)).text


@pytest.mark.parametrize("detail", ORDER)
def test_markdown_never_contains_removed_content(detail: Detail) -> None:
    out = markdown(detail)
    for removed in ("dataLayer", "font-family", "cookies", "SAVE20", "pixel.gif", "Share on X"):
        assert removed not in out
    assert "# The Best Trail Running Shoes of the Year" in out
    assert "| Peak Runner 3 | 9/10 | 280 g |" in out


@pytest.mark.parametrize("detail", [Detail.MINIMAL, Detail.LOW, Detail.MEDIUM])
def test_markdown_below_high_drops_chrome(detail: Detail) -> None:
    out = markdown(detail)
    for chrome in ("Gear Weekly", "Packs", "Best hiking boots", "Privacy"):
        assert chrome not in out


def test_markdown_high_includes_chrome() -> None:
    out = markdown(Detail.HIGH)
    assert "[Packs](/packs)" in out
    assert "Best hiking boots" in out


def test_markdown_low_has_no_urls() -> None:
    out = markdown(Detail.LOW)
    assert "](" not in out
    assert "testing method" in out
    assert "Twelve pairs of trail shoes lined up" in out


def test_markdown_minimal_drops_images() -> None:
    assert "Twelve pairs" not in markdown(Detail.MINIMAL)


def test_markdown_medium_keeps_clean_urls_and_images() -> None:
    out = markdown(Detail.MEDIUM)
    assert "[testing method](https://example.com/method?id=7)" in out
    assert "![Twelve pairs of trail shoes lined up](/img/shoes.jpg)" in out


def test_markdown_reports_strategy() -> None:
    result = html_to_markdown(ARTICLE, markdown_settings(Detail.MEDIUM))
    assert result.notices == ("main content found by: main element",)


def test_markdown_warns_when_little_text_is_kept() -> None:
    page = (
        b"<body><main><p>tiny</p></main><div>"
        + b"<p>"
        + b"lots of other text " * 100
        + b"</p></div></body>"
    )
    result = html_to_markdown(page, markdown_settings(Detail.MEDIUM))
    assert any("--detail high" in notice for notice in result.notices)


@pytest.mark.parametrize("detail", ORDER)
def test_html_never_contains_removed_content(detail: Detail) -> None:
    out = html(detail)
    for removed in (
        "<script",
        "<style",
        "<link",
        "dataLayer",
        "SAVE20",
        "pixel.gif",
        "onclick",
        "<!--",
    ):
        assert removed not in out
    assert out.startswith("<!DOCTYPE html>\n<html")


@pytest.mark.parametrize("detail", [Detail.MINIMAL, Detail.LOW])
def test_html_low_levels_collapse_chrome(detail: Detail) -> None:
    out = html(detail)
    assert '<header data-collapsed="6 links, 7 words"></header>' in out
    assert '<footer data-collapsed="3 links, 6 words"></footer>' in out
    assert "<h1>The Best Trail Running Shoes of the Year</h1>" in out


def test_html_minimal_has_no_attributes_except_placeholders() -> None:
    out = html(Detail.MINIMAL)
    assert "href=" not in out
    assert "class=" not in out
    assert "<strong>" not in out
    assert "Twelve pairs of trail shoes lined up" in out


@pytest.mark.parametrize("detail", ORDER)
def test_main_content_inside_a_junk_wrapper_survives(detail: Detail) -> None:
    page = b'<body><div class="modal-open"><main><p>the real story</p></main></div></body>'
    assert "the real story" in html_to_markdown(page, markdown_settings(detail)).text
    assert "the real story" in html_to_html(page, html_settings(detail)).text


def test_html_puts_each_block_on_its_own_line() -> None:
    page = (
        b"<body><main><h1>Title</h1><p>one <b>bold</b> two</p><ul><li>x</li><li>y</li></ul>"
        b"<table><tr><td>1</td><td>2</td></tr></table></main></body>"
    )
    lines = html_to_html(page, html_settings(Detail.MEDIUM)).text.splitlines()
    for line in ("<h1>Title</h1>", "<p>one <b>bold</b> two</p>", "<li>x</li>", "<li>y</li>"):
        assert line in lines
    assert "<tr><td>1</td><td>2</td></tr>" in lines


def test_html_line_breaks_leave_preformatted_text_alone() -> None:
    page = (
        b"<body><main><p>before</p><pre>line one\n    indented <span>s</span></pre></main></body>"
    )
    out = html_to_html(page, html_settings(Detail.HIGH)).text
    assert "<pre>line one\n    indented <span>s</span></pre>" in out


def test_html_keeps_non_breaking_space_after_newline() -> None:
    page = "<body><main><p>a\n\u00a0b</p></main></body>".encode()
    out = html_to_html(page, html_settings(Detail.MEDIUM)).text
    assert "\n\u00a0b" in out or "\n&nbsp;b" in out


def test_html_minimal_keeps_line_breaks() -> None:
    page = b"<body><main><p>first line<br>second line</p><hr><p>after</p></main></body>"
    out = html_to_html(page, html_settings(Detail.MINIMAL)).text
    assert "first line<br>second line" in out
    assert "<hr>" in out


def test_html_has_no_blank_lines() -> None:
    for detail in ORDER:
        assert "\n\n" not in html(detail)
        assert "  " not in html(detail).replace("<pre>", "")


def test_html_flattens_wrappers() -> None:
    assert "<div><div>" not in html(Detail.MEDIUM)


def test_html_medium_keeps_chrome_and_form_attributes_but_collapses_junk() -> None:
    out = html(Detail.MEDIUM)
    assert '<a href="/packs">Packs</a>' in out
    assert '<div data-collapsed="0 links, 8 words"></div>' in out
    assert '<input type="email" name="email" placeholder="you@example.com">' in out
    assert '<img src="/img/shoes.jpg" alt="Twelve pairs of trail shoes lined up">' in out
    assert "class=" not in out


def test_html_high_keeps_everything_but_always_removed() -> None:
    out = html(Detail.HIGH)
    assert 'id="cookie-banner"' in out
    assert 'class="wrapper"' in out
    assert "data-collapsed" not in out


def page_html(body: str, detail: Detail) -> str:
    return html_to_html(f"<body><main>{body}</main></body>".encode(), html_settings(detail)).text


def test_html_minimal_separates_unwrapped_adjacent_elements() -> None:
    out = page_html(
        "<div><span>Season Acquisition Limit</span><b>No Limit</b></div>", Detail.MINIMAL
    )
    assert "<div>Season Acquisition Limit No Limit</div>" in out


def test_html_kept_tags_gain_no_spaces() -> None:
    out = page_html("<div><span>a</span><span>b</span></div>", Detail.MEDIUM)
    assert "<div><span>a</span><span>b</span></div>" in out


@pytest.mark.parametrize("detail", [Detail.MINIMAL, Detail.LOW])
def test_html_alt_text_is_separated_and_deduplicated(detail: Detail) -> None:
    out = page_html(
        '<p>foo<img alt="bar">baz</p><p><img alt="Brock Purdy"><img alt="Brock Purdy"></p>', detail
    )
    assert "<p>foo bar baz</p>" in out
    assert "<p>Brock Purdy</p>" in out


def test_html_alt_text_separated_by_text_is_not_deduplicated() -> None:
    out = page_html('<p><img alt="x"> one <img alt="x"> two</p>', Detail.LOW)
    assert "<p>x one x two</p>" in out


@pytest.mark.parametrize("detail", [Detail.MINIMAL, Detail.LOW])
def test_html_keeps_table_spans(detail: Detail) -> None:
    out = page_html(
        '<table><tr><th colspan="2">h</th></tr><tr><td rowspan="2">a</td><td>b</td></tr></table>',
        detail,
    )
    assert '<th colspan="2">h</th>' in out
    assert '<td rowspan="2">a</td>' in out


def test_html_minimal_unwraps_cell_wrappers() -> None:
    out = page_html(
        "<table><tr><th><div>Player</div></th><td><div><div>Brock Purdy</div>"
        "<div><span>SF</span><span>QB</span></div></div></td>"
        '<td><div data-collapsed="1 links, 2 words"></div></td></tr></table>',
        Detail.MINIMAL,
    )
    assert "<th>Player</th><td>Brock Purdy SF QB</td>" in out
    assert '<td><div data-collapsed="1 links, 2 words"></div></td>' in out


@pytest.mark.parametrize("convert", [markdown, html])
def test_output_grows_with_detail(convert: object) -> None:
    assert callable(convert)
    sizes = [len(convert(detail)) for detail in ORDER]
    assert sizes == sorted(sizes)
