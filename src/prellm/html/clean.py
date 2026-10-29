import re

from lxml import etree
from lxml.html import HtmlElement

REMOVED_TAGS = ("script", "style", "noscript", "template", "iframe", "link", "meta")

_HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)
_LEADING_INT = re.compile(r"^\s*(\d+)")


def clean_always(root: HtmlElement) -> None:
    """Remove what is never content, at every detail level and in every format."""
    for node in list(root.iter(etree.Comment, etree.ProcessingInstruction)):
        _drop_node(node)
    for element in list(root.iter(*REMOVED_TAGS)):
        element.drop_tree()
    for element in list(root.iter()):
        if isinstance(element.tag, str) and _is_hidden(element):
            if element.tag in ("html", "body"):
                raise ValueError(
                    f"page marks its <{element.tag}> element as hidden; nothing would be visible"
                )
            element.drop_tree()
    for svg in list(root.iter("svg")):
        _replace_inline_svg(svg)
    for image in list(root.iter("img")):
        if _is_tracking_pixel(image):
            image.drop_tree()
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        for name in list(element.attrib):
            if name.lower().startswith("on") or name.lower() == "style":
                del element.attrib[name]


def _is_hidden(element: HtmlElement) -> bool:
    if element.get("hidden") is not None:
        return True
    if (element.get("aria-hidden") or "").lower() == "true":
        return True
    return bool(_HIDDEN_STYLE.search(element.get("style") or ""))


def _is_tracking_pixel(image: HtmlElement) -> bool:
    width = _leading_int(image.get("width"))
    height = _leading_int(image.get("height"))
    return width is not None and height is not None and width <= 1 and height <= 1


def _leading_int(value: str | None) -> int | None:
    match = _LEADING_INT.match(value or "")
    return int(match.group(1)) if match else None


def _replace_inline_svg(svg: HtmlElement) -> None:
    title = svg.find(".//title")
    alt = svg.get("aria-label") or (title.text_content().strip() if title is not None else "")
    if not alt:
        svg.drop_tree()
        return
    image = svg.makeelement("img", {"alt": alt})
    image.tail = svg.tail
    parent = svg.getparent()
    if parent is not None:
        parent.replace(svg, image)


def _drop_node(node: etree._Element) -> None:
    parent = node.getparent()
    if parent is None:
        return
    if node.tail:
        previous = node.getprevious()
        if previous is not None:
            previous.tail = (previous.tail or "") + node.tail
        else:
            parent.text = (parent.text or "") + node.tail
    parent.remove(node)
