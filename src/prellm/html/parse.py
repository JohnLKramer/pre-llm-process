import codecs
import re

import lxml.etree
import lxml.html
from lxml.html import HtmlElement

_META_CHARSET = re.compile(rb"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9_\-:.]+)""", re.I)
_SNIFF_BYTES = 4096
# Longest first: the UTF-32 LE BOM starts with the UTF-16 LE BOM.
_BOMS = (
    (codecs.BOM_UTF32_LE, "utf-32"),
    (codecs.BOM_UTF32_BE, "utf-32"),
    (codecs.BOM_UTF16_LE, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16"),
    (codecs.BOM_UTF8, "utf-8-sig"),
)


class HtmlDecodeError(ValueError):
    pass


def decode_html(data: bytes) -> str:
    """Decode with the BOM or declared charset, else strict UTF-8. Never substitutes characters."""
    for bom, codec in _BOMS:
        if data.startswith(bom):
            try:
                return data.decode(codec)
            except UnicodeDecodeError as error:
                raise HtmlDecodeError(
                    f"page has a {codec} byte-order mark but is not valid {codec}: {error}"
                ) from error
    match = _META_CHARSET.search(data[:_SNIFF_BYTES])
    if match:
        declared = match.group(1).decode("ascii")
        try:
            return data.decode(declared)
        except LookupError as error:
            raise HtmlDecodeError(f"page declares unknown charset {declared!r}") from error
        except UnicodeDecodeError as error:
            raise HtmlDecodeError(f"page is not valid {declared}: {error}") from error
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise HtmlDecodeError(
            f"page declares no charset and is not valid UTF-8: {error}"
        ) from error


def parse_html(data: bytes) -> HtmlElement:
    text = decode_html(data)
    parser = lxml.html.HTMLParser(encoding="utf-8", remove_comments=False)
    root: HtmlElement = lxml.html.document_fromstring(text.encode("utf-8"), parser=parser)
    return root


def body_of(root: HtmlElement) -> HtmlElement:
    body = root.find("body")
    if body is None:
        raise ValueError("parsed document has no <body>")
    result: HtmlElement = body
    return result


def normalized_text(element: HtmlElement) -> str:
    return " ".join(element.text_content().split())


def repeated_alt_images(root: HtmlElement) -> set[HtmlElement]:
    """Images whose alt text equals the previous image's with no text between the two."""
    repeated: set[HtmlElement] = set()
    previous_alt: str | None = None
    for event, element in lxml.etree.iterwalk(root, events=("start", "end")):
        if event == "start" and element.tag == "img":
            alt = " ".join((element.get("alt") or "").split())
            if alt == previous_alt:
                repeated.add(element)
            previous_alt = alt
        elif ((element.text if event == "start" else element.tail) or "").strip():
            previous_alt = None
    return repeated
