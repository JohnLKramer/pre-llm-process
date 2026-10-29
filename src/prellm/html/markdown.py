import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import lxml.html
from lxml.html import HtmlElement

from prellm.html.parse import repeated_alt_images
from prellm.levels import ImageMode, MarkdownSettings

BLOCK_TAGS = frozenset(
    {
        "address", "article", "aside", "blockquote", "body", "dd", "details", "div", "dl", "dt",
        "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6",
        "header", "hr", "html", "li", "main", "nav", "ol", "p", "pre", "section", "summary",
        "table", "ul",
    }
)  # fmt: skip
TRACKING_PARAMETERS = frozenset({"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src"})
TABLE_TAGS = frozenset({"table", "caption", "thead", "tbody", "tfoot", "tr", "th", "td"})
DROPPED_IN_TABLES = frozenset({"colgroup", "col", "img"})

_LINE_BREAK = "\x00"
_WHITESPACE = re.compile(r"\s+")
_AROUND_TAG = re.compile(r"\s*(<[^>]+>)\s*")


def to_markdown(element: HtmlElement, settings: MarkdownSettings) -> str:
    skipped = repeated_alt_images(element) if settings.images is ImageMode.ALT else set()
    blocks = _Writer(settings, skipped).blocks(element)
    text = "\n\n".join(blocks).strip()
    return text + "\n" if text else ""


def strip_tracking(url: str) -> str:
    parts = urlsplit(url)
    if not parts.query:
        return url
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.startswith("utm_") and key not in TRACKING_PARAMETERS
    ]
    return urlunsplit(parts._replace(query=urlencode(query)))


class _Writer:
    def __init__(self, settings: MarkdownSettings, skipped_images: set[HtmlElement]) -> None:
        self.settings = settings
        self.skipped_images = skipped_images

    def blocks(self, element: HtmlElement) -> list[str]:
        tag = element.tag
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = self._inline_text(element).replace("\n", " ")
            return [f"{'#' * int(tag[1])} {text}"] if text else []
        if tag == "p":
            text = self._inline_text(element)
            return [text] if text else []
        if tag == "pre":
            return ["```\n" + element.text_content().strip("\n") + "\n```"]
        if tag == "hr":
            return ["---"]
        if tag == "blockquote":
            inner = "\n\n".join(self._child_blocks(element))
            return ["\n".join(f"> {line}".rstrip() for line in inner.splitlines())] if inner else []
        if tag in ("ul", "ol"):
            listing = self._list(element)
            return [listing] if listing else []
        if tag == "table":
            return [self._table(element)]
        if tag == "dt":
            text = self._inline_text(element)
            return [f"**{text}**"] if text else []
        return self._child_blocks(element)

    def _child_blocks(self, element: HtmlElement) -> list[str]:
        blocks: list[str] = []
        inline: list[str] = []

        def flush() -> None:
            text = _finish_inline("".join(inline))
            if text:
                blocks.append(text)
            inline.clear()

        inline.append(element.text or "")
        for child in element:
            if isinstance(child.tag, str) and child.tag in BLOCK_TAGS:
                flush()
                blocks.extend(self.blocks(child))
            elif isinstance(child.tag, str):
                inline.append(_separator(child) + self._inline(child))
            inline.append(child.tail or "")
        flush()
        return blocks

    def _inline_text(self, element: HtmlElement) -> str:
        return _finish_inline(self._inline_children(element))

    def _inline_children(self, element: HtmlElement) -> str:
        parts = [element.text or ""]
        for child in element:
            if isinstance(child.tag, str):
                parts.append(_separator(child) + self._inline(child))
            parts.append(child.tail or "")
        return "".join(parts)

    def _inline(self, element: HtmlElement) -> str:
        tag = element.tag
        if tag == "br":
            return _LINE_BREAK
        if tag == "img":
            return self._image(element)
        if tag == "code":
            code = " ".join(element.text_content().split())
            return f"`{code}`" if code else ""
        content = self._inline_children(element)
        if tag in BLOCK_TAGS:
            content = f" {content} "
        if tag == "a":
            return self._link(element, content)
        if tag in ("strong", "b"):
            return _wrap(content, "**")
        if tag in ("em", "i"):
            return _wrap(content, "*")
        return content

    def _link(self, element: HtmlElement, content: str) -> str:
        href = element.get("href")
        text = content.strip()
        if not text or not self.settings.keep_link_urls or not href or href.startswith("#"):
            return content
        return f"[{text}]({strip_tracking(href)})"

    def _image(self, element: HtmlElement) -> str:
        alt = " ".join((element.get("alt") or "").split())
        mode = self.settings.images
        if mode is ImageMode.DROP:
            return ""
        src = element.get("src")
        if mode is ImageMode.REF and src:
            return f"![{alt}]({src})"
        if not alt or element in self.skipped_images:
            return ""
        return f" {alt} "

    def _list(self, element: HtmlElement) -> str:
        items = []
        number = 1
        for child in element:
            if child.tag != "li":
                continue
            marker = f"{number}. " if element.tag == "ol" else "- "
            number += 1
            body = "\n".join(self._child_blocks(child))
            if not body:
                continue
            indent = " " * len(marker)
            lines = body.splitlines()
            rest = [f"{indent}{line}" if line else "" for line in lines[1:]]
            items.append("\n".join([marker + lines[0], *rest]))
        return "\n".join(items)

    def _table(self, table: HtmlElement) -> str:
        rows = [row for row in table.iter("tr") if _nearest_table(row) is table]
        complex_table = any(
            cell.get("rowspan") or cell.get("colspan") for cell in table.iter("td", "th")
        ) or any(nested is not table for nested in table.iter("table"))
        has_cells = any(cell.tag in ("td", "th") for row in rows for cell in row)
        if complex_table or not rows or not has_cells:
            return _html_table(table)
        grid = [
            [
                self._inline_text(cell).replace("\n", " ").replace("|", "\\|")
                for cell in row
                if cell.tag in ("td", "th")
            ]
            for row in rows
        ]
        width = max(len(row) for row in grid)
        grid = [row + [""] * (width - len(row)) for row in grid]
        lines = [
            "| " + " | ".join(grid[0]) + " |",
            "| " + " | ".join(["---"] * width) + " |",
        ]
        lines.extend("| " + " | ".join(row) + " |" for row in grid[1:])
        return "\n".join(lines)


def _finish_inline(text: str) -> str:
    collapsed = _WHITESPACE.sub(" ", text)
    lines = [line.strip() for line in collapsed.split(_LINE_BREAK)]
    return "\n".join(lines).strip()


def _separator(element: HtmlElement) -> str:
    previous = element.getprevious()
    adjacent = previous is not None and isinstance(previous.tag, str) and not previous.tail
    return " " if adjacent else ""


def _wrap(content: str, marker: str) -> str:
    text = content.strip()
    return f"{marker}{text}{marker}" if text else content


def _nearest_table(element: HtmlElement) -> HtmlElement | None:
    for ancestor in element.iterancestors("table"):
        return ancestor
    return None


def _html_table(table: HtmlElement) -> str:
    """Compact HTML for a table markdown can't express: table tags and span attributes only."""
    copy = lxml.html.fromstring(lxml.html.tostring(table, with_tail=False))
    for element in list(copy.iter()):
        if not isinstance(element.tag, str):
            continue
        if element.tag in DROPPED_IN_TABLES:
            element.drop_tree()
        elif element.tag not in TABLE_TAGS:
            element.tail = " " + (element.tail or "")
            element.drop_tag()
        else:
            for name in list(element.attrib):
                if name not in ("rowspan", "colspan"):
                    del element.attrib[name]
    html: str = lxml.html.tostring(copy, encoding="unicode")
    return _AROUND_TAG.sub(r"\1", _WHITESPACE.sub(" ", html)).strip()
