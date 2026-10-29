import pytest

from prellm.html.markdown import strip_tracking, to_markdown
from prellm.html.parse import body_of, parse_html
from prellm.levels import ImageMode, MarkdownSettings

FULL = MarkdownSettings(main_content_only=False, keep_link_urls=True, images=ImageMode.REF)
TEXT_ONLY = MarkdownSettings(main_content_only=True, keep_link_urls=False, images=ImageMode.ALT)


def md(html: str, settings: MarkdownSettings = FULL) -> str:
    return to_markdown(body_of(parse_html(html.encode("utf-8"))), settings)


def test_headings_and_paragraphs() -> None:
    assert md("<h1>Title</h1><p>One\n  two</p><h3>Sub</h3>") == "# Title\n\nOne two\n\n### Sub\n"


def test_inline_formatting() -> None:
    assert md("<p>a <strong>b</strong> <em>c</em> <code>d()</code></p>") == "a **b** *c* `d()`\n"


def test_links_keep_urls_without_tracking() -> None:
    out = md('<p><a href="https://x.com/a?utm_source=s&amp;id=1&amp;fbclid=f">A</a></p>')
    assert out == "[A](https://x.com/a?id=1)\n"


def test_links_become_text_when_urls_dropped() -> None:
    assert md('<p>See <a href="/x">the docs</a>.</p>', TEXT_ONLY) == "See the docs.\n"


def test_fragment_links_are_plain_text() -> None:
    assert md('<p><a href="#top">Top</a></p>') == "Top\n"


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (ImageMode.DROP, "Before after\n"),
        (ImageMode.ALT, "Before A cat after\n"),
        (ImageMode.REF, "Before ![A cat](/cat.png) after\n"),
    ],
)
def test_image_modes(mode: ImageMode, expected: str) -> None:
    settings = MarkdownSettings(main_content_only=False, keep_link_urls=True, images=mode)
    assert md('<p>Before <img src="/cat.png" alt="A cat"> after</p>', settings) == expected


def test_image_without_src_uses_alt_text() -> None:
    assert md('<p><img alt="Cart"></p>') == "Cart\n"


def test_nested_lists() -> None:
    html = "<ul><li>a</li><li>b<ul><li>c</li></ul></li></ul><ol><li>x</li><li>y</li></ol>"
    assert md(html) == "- a\n- b\n  - c\n\n1. x\n2. y\n"


def test_pre_keeps_whitespace() -> None:
    assert md("<pre><code>a = 1\n  b = 2</code></pre>") == "```\na = 1\n  b = 2\n```\n"


def test_blockquote() -> None:
    assert md("<blockquote><p>q1</p><p>q2</p></blockquote>") == "> q1\n>\n> q2\n"


def test_simple_table_becomes_pipe_table() -> None:
    html = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>x|y</td></tr></table>"
    assert md(html) == "| A | B |\n| --- | --- |\n| 1 | x\\|y |\n"


def test_table_with_colspan_stays_html() -> None:
    html = (
        '<table class="t"><tr><td colspan="2">wide</td></tr><tr><td>a</td><td>b</td></tr></table>'
    )
    assert md(html) == (
        '<table><tr><td colspan="2">wide</td></tr><tr><td>a</td><td>b</td></tr></table>\n'
    )


def test_complex_table_keeps_only_table_tags() -> None:
    html = (
        '<table><colgroup><col></colgroup><tr><th colspan="2"><div><span>Player</span></div></th></tr>'
        '<tr><td><div><img src="/p.png"><span><a href="/p">Brock Purdy</a></span><span>SF</span></div></td>'
        "<td><button><span>MOVE</span></button></td></tr></table>"
    )
    assert md(html) == (
        '<table><tr><th colspan="2">Player</th></tr><tr><td>Brock Purdy SF</td><td>MOVE</td></tr></table>\n'
    )


def test_line_breaks() -> None:
    assert md("<p>one<br>two</p>") == "one\ntwo\n"


def test_div_soup_becomes_paragraphs() -> None:
    assert md("<div>one</div><div><span>two</span> three</div>") == "one\n\ntwo three\n"


def test_strip_tracking_leaves_clean_urls_alone() -> None:
    assert strip_tracking("/a/b") == "/a/b"
    assert strip_tracking("https://x.com/?ref=home") == "https://x.com/"


def test_text_after_complex_table_is_not_duplicated() -> None:
    out = md('<table><tr><td colspan="2">x</td></tr></table>after')
    assert out.count("after") == 1
    assert "<div" not in out


def test_block_children_in_table_cell_are_separated() -> None:
    out = md("<table><tr><td><p>a</p><p>b</p></td></tr></table>")
    assert out == "| a b |\n| --- |\n"


def test_block_children_in_link_are_separated() -> None:
    assert md('<a href="/x"><div>Title</div><div>Desc</div></a>') == "[Title Desc](/x)\n"


def test_table_without_cells_is_not_a_pipe_table() -> None:
    assert "|" not in md("<table><tr></tr></table>")


def test_adjacent_elements_are_separated() -> None:
    html = (
        "<div><span>IR</span><span>Add</span><span>Drop</span></div>"
        "<div><span>Season Acquisition Limit</span><span>No Limit</span></div>"
    )
    assert md(html) == "IR Add Drop\n\nSeason Acquisition Limit No Limit\n"


def test_adjacent_elements_add_no_space_inside_markers_or_cells() -> None:
    html = '<p><strong><span>a</span><span>b</span></strong><a href="/x"><em>c</em><span>d</span></a></p>'
    assert md(html) == "**a b** [*c* d](/x)\n"
    assert (
        md("<table><tr><td><span>a</span><span>b</span></td></tr></table>") == "| a b |\n| --- |\n"
    )


def test_alt_text_is_separated_from_neighbouring_text() -> None:
    assert md('<p>foo<img alt="bar">baz</p>', TEXT_ONLY) == "foo bar baz\n"


def test_repeated_alt_text_is_skipped() -> None:
    assert (
        md('<p><img alt="Brock Purdy"><img alt="Brock Purdy"> SF</p>', TEXT_ONLY)
        == "Brock Purdy SF\n"
    )


def test_alt_text_separated_by_text_is_not_deduplicated() -> None:
    assert md('<p><img alt="x"> one <img alt="x"> two</p>', TEXT_ONLY) == "x one x two\n"


def test_ref_images_are_not_deduplicated() -> None:
    assert md('<p><img src="/a.png" alt="x"><img src="/b.png" alt="x"></p>').count("![x]") == 2
