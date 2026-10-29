import codecs

import lxml.html
import pytest

from prellm.html.clean import clean_always
from prellm.html.parse import HtmlDecodeError, body_of, decode_html, parse_html


def cleaned_body(html: str) -> str:
    root = parse_html(html.encode("utf-8"))
    clean_always(root)
    result: str = lxml.html.tostring(body_of(root), encoding="unicode")
    return result


def test_decode_uses_declared_charset() -> None:
    data = '<meta charset="windows-1252"><p>café</p>'.encode("cp1252")
    assert "café" in decode_html(data)


def test_decode_defaults_to_utf8() -> None:
    assert "naïve" in decode_html("<p>naïve</p>".encode())


def test_decode_rejects_undeclared_non_utf8() -> None:
    with pytest.raises(HtmlDecodeError, match="not valid UTF-8"):
        decode_html("<p>café</p>".encode("cp1252"))


def test_decode_rejects_unknown_charset() -> None:
    with pytest.raises(HtmlDecodeError, match="unknown charset"):
        decode_html(b'<meta charset="klingon"><p>hi</p>')


def test_removes_scripts_styles_and_comments() -> None:
    body = cleaned_body(
        "<body><script>x()</script><style>p{}</style><noscript>n</noscript>"
        "<template><p>t</p></template><iframe src='/ad'></iframe><!-- c --><p>keep</p></body>"
    )
    assert body == "<body><p>keep</p></body>"


def test_removes_hidden_elements() -> None:
    body = cleaned_body(
        '<body><p hidden>a</p><p aria-hidden="true">b</p><p style="display: none">c</p>'
        '<p style="visibility:hidden">d</p><p>keep</p></body>'
    )
    assert body == "<body><p>keep</p></body>"


def test_removes_tracking_pixels_but_keeps_real_images() -> None:
    body = cleaned_body(
        '<body><img src="/t.gif" width="1" height="1"><img src="/real.png" width="200px" height="1"></body>'
    )
    assert "/t.gif" not in body
    assert "/real.png" in body


def test_removes_event_handlers_and_inline_style() -> None:
    body = cleaned_body(
        '<body><button onclick="go()" style="color:red" type="submit">Go</button></body>'
    )
    assert body == '<body><button type="submit">Go</button></body>'


def test_inline_svg_becomes_image_with_alt_text() -> None:
    body = cleaned_body(
        '<body><svg aria-label="Cart"><path d="M0 0"/></svg> items'
        "<svg><title>Search</title></svg><svg><path/></svg></body>"
    )
    assert body == '<body><img alt="Cart"> items<img alt="Search"></body>'


def test_comment_tail_text_is_kept() -> None:
    assert cleaned_body("<body><p>a<!-- c -->b</p></body>") == "<body><p>ab</p></body>"


def test_decode_strips_utf8_bom() -> None:
    text = decode_html(codecs.BOM_UTF8 + "<p>café</p>".encode())
    assert not text.startswith("\ufeff")
    assert "café" in text


def test_decode_utf16_le_bom() -> None:
    assert "café" in decode_html(codecs.BOM_UTF16_LE + "<p>café</p>".encode("utf-16-le"))


def test_decode_utf32_le_bom_is_not_read_as_utf16() -> None:
    text = decode_html(codecs.BOM_UTF32_LE + "<p>café</p>".encode("utf-32-le"))
    assert text == "<p>café</p>"


def test_decode_rejects_invalid_bytes_after_bom() -> None:
    with pytest.raises(HtmlDecodeError, match="byte-order mark"):
        decode_html(codecs.BOM_UTF8 + b"<p>\xff</p>")


def test_decode_honors_http_equiv_content_type() -> None:
    data = (
        '<meta http-equiv="Content-Type" content="text/html; charset=windows-1252"><p>café</p>'
    ).encode("cp1252")
    assert "café" in decode_html(data)


def test_decode_rejects_invalid_bytes_under_declared_charset() -> None:
    with pytest.raises(HtmlDecodeError, match="not valid utf-8"):
        decode_html(b'<meta charset="utf-8"><p>\xff</p>')


@pytest.mark.parametrize("tag", ["html", "body"])
def test_hidden_root_raises(tag: str) -> None:
    root = parse_html(
        f"<html{' hidden' if tag == 'html' else ''}><body{' hidden' if tag == 'body' else ''}><p>x</p></body></html>".encode()
    )
    with pytest.raises(ValueError, match=f"<{tag}> element as hidden"):
        clean_always(root)
