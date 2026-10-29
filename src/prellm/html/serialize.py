import re

import lxml.html
from lxml.html import HtmlElement

from prellm.html.parse import repeated_alt_images
from prellm.levels import HtmlSettings, ImageMode

STRUCTURAL_TAGS = frozenset(
    {
        "html", "body", "main", "article", "section", "nav", "header", "footer", "aside",
        "h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "li", "dl", "dt", "dd",
        "table", "thead", "tbody", "tr", "th", "td", "form", "label", "input", "select",
        "option", "textarea", "button", "pre", "code", "blockquote", "div", "br", "hr",
    }
)  # fmt: skip
WRAPPER_TAGS = frozenset({"div", "span"})
CELL_TAGS = frozenset({"td", "th"})
COLLAPSED_ATTRIBUTE = "data-collapsed"
ALWAYS_KEPT_ATTRIBUTES = frozenset({COLLAPSED_ATTRIBUTE, "rowspan", "colspan"})
PREFORMATTED_TAGS = frozenset({"pre", "textarea"})
LINE_TAGS = frozenset(
    {
        "html", "head", "title", "body", "main", "article", "section", "nav", "header", "footer",
        "aside", "div", "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "dl", "dt",
        "dd", "table", "caption", "thead", "tbody", "tfoot", "tr", "form", "fieldset", "legend",
        "blockquote", "figure", "figcaption", "details", "summary", "address", "pre", "hr",
        "textarea", "select", "option",
    }
)  # fmt: skip

_SPACE_RUN = re.compile(r"[ \t\f\r]+")
_NEWLINE_RUN = re.compile(r" ?\n[ \t\n\f\r]*")
# A Unicode noncharacter: pages never contain it, and lxml accepts it in text.
_BOUNDARY = "\ufdd0"
_TEXT_BOUNDARY = re.compile(rf"(?<=[^\s{_BOUNDARY}]){_BOUNDARY}+(?=[^\s{_BOUNDARY}])")


def images_to_alt_text(body: HtmlElement) -> None:
    skipped = repeated_alt_images(body)
    for image in list(body.iter("img")):
        alt = (image.get("alt") or "").strip()
        replace_with_text(image, "" if image in skipped else _BOUNDARY + alt + _BOUNDARY)


def unwrap_non_structural(body: HtmlElement) -> None:
    for element in list(body.iter()):
        if not isinstance(element.tag, str) or element.get(COLLAPSED_ATTRIBUTE) is not None:
            continue
        if element.tag not in STRUCTURAL_TAGS or _is_cell_wrapper(element):
            _drop_tag_separated(element)


def _is_cell_wrapper(element: HtmlElement) -> bool:
    return element.tag in WRAPPER_TAGS and any(
        ancestor.tag in CELL_TAGS for ancestor in element.iterancestors()
    )


def resolve_boundaries(body: HtmlElement) -> None:
    """Turn a boundary left by a removed tag into a space only where text meets text."""
    for element in body.iter():
        element.text = _resolve(element.text)
        element.tail = _resolve(element.tail)


def _drop_tag_separated(element: HtmlElement) -> None:
    previous = element.getprevious()
    if previous is not None and isinstance(previous.tag, str) and not previous.tail:
        previous.tail = _BOUNDARY
    following = element.getnext()
    if following is not None and isinstance(following.tag, str) and not element.tail:
        element.tail = _BOUNDARY
    element.drop_tag()


def _resolve(text: str | None) -> str | None:
    if text is None or _BOUNDARY not in text:
        return text
    return _TEXT_BOUNDARY.sub(" ", text).replace(_BOUNDARY, "")


def flatten_wrappers(body: HtmlElement) -> None:
    for element in reversed(list(body.iter(*WRAPPER_TAGS))):
        if element.getparent() is None or len(element) != 1:
            continue
        child = element[0]
        if (element.text or "").strip() or (child.tail or "").strip():
            continue
        if not isinstance(child.tag, str) or element.get(COLLAPSED_ATTRIBUTE) is not None:
            continue
        child.tail = element.tail
        parent = element.getparent()
        parent.replace(element, child)


def filter_attributes(root: HtmlElement, kept: frozenset[str]) -> None:
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        for name in list(element.attrib):
            if name not in kept and name not in ALWAYS_KEPT_ATTRIBUTES:
                del element.attrib[name]


def collapse_whitespace(root: HtmlElement) -> None:
    """Collapse whitespace runs outside pre and textarea; a run containing a newline becomes one."""
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        preformatted = element.tag in PREFORMATTED_TAGS or any(
            ancestor.tag in PREFORMATTED_TAGS for ancestor in element.iterancestors()
        )
        if not preformatted:
            element.text = _collapse(element.text)
        if not (preformatted and element.tag not in PREFORMATTED_TAGS):
            element.tail = _collapse(element.tail)


def _collapse(text: str | None) -> str | None:
    if text is None:
        return None
    return _NEWLINE_RUN.sub("\n", _SPACE_RUN.sub(" ", text))


def break_lines(root: HtmlElement) -> None:
    """Start and end every block-level element on its own line; table rows stay on one line."""
    inline_inside = PREFORMATTED_TAGS | CELL_TAGS
    for element in root.iter(*LINE_TAGS):
        parent = element.getparent()
        if parent is None or any(
            ancestor.tag in inline_inside for ancestor in element.iterancestors()
        ):
            continue
        previous = element.getprevious()
        if previous is not None:
            previous.tail = (previous.tail or "") + "\n"
        else:
            parent.text = (parent.text or "") + "\n"
        element.tail = "\n" + (element.tail or "")


def serialize(root: HtmlElement) -> str:
    break_lines(root)
    collapse_whitespace(root)
    html: str = lxml.html.tostring(root, encoding="unicode", method="html")
    return "<!DOCTYPE html>\n" + html + "\n"


def replace_with_text(element: HtmlElement, text: str) -> None:
    """Replace element with text, keeping its tail."""
    parent = element.getparent()
    if parent is None:
        return
    joined = text + (element.tail or "")
    previous = element.getprevious()
    if previous is not None:
        previous.tail = (previous.tail or "") + joined
    else:
        parent.text = (parent.text or "") + joined
    parent.remove(element)


def apply_html_settings(root: HtmlElement, body: HtmlElement, settings: HtmlSettings) -> None:
    if settings.images is ImageMode.ALT:
        images_to_alt_text(body)
    if settings.structural_only:
        unwrap_non_structural(body)
    resolve_boundaries(body)
    if settings.flatten_wrappers:
        flatten_wrappers(body)
    filter_attributes(root, settings.kept_attributes)
