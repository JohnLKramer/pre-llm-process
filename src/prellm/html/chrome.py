import re
from enum import StrEnum

from lxml.html import HtmlElement

from prellm.html.parse import normalized_text


class RegionKind(StrEnum):
    CHROME = "chrome"
    JUNK = "junk"


CHROME_TAGS = frozenset({"nav", "header", "footer", "aside"})
CHROME_ROLES = frozenset({"navigation", "banner", "contentinfo", "complementary"})
CONTENT_CONTAINERS = frozenset({"article", "main"})
LINK_DENSITY_TAGS = frozenset({"div", "section", "ul"})
NEVER_REGIONS = frozenset({"html", "head", "body", "main", "article"})
JUNK_TOKENS = frozenset(
    {
        "ad", "ads", "advert", "advertisement", "sponsor", "sponsored",
        "cookie", "cookies", "consent", "gdpr", "newsletter", "subscribe",
        "modal", "popup", "share", "sharing", "social",
    }
)  # fmt: skip
MIN_LINKS_FOR_DENSITY = 5
LINK_DENSITY_THRESHOLD = 0.5
# Menus have short links ("Shoes", "Sign in"); headline lists have sentence-length links.
MAX_AVERAGE_WORDS_PER_NAV_LINK = 4

_TOKEN_SPLIT = re.compile(r"[\s\-_]+")


def find_regions(body: HtmlElement) -> list[tuple[HtmlElement, RegionKind]]:
    """Outermost chrome and junk regions, in document order. Regions are not nested."""
    regions: list[tuple[HtmlElement, RegionKind]] = []
    holders = {
        ancestor for anchor in _main_content_anchors(body) for ancestor in anchor.iterancestors()
    }

    def walk(element: HtmlElement) -> None:
        for child in element:
            if not isinstance(child.tag, str):
                continue
            kind = None if child in holders else classify(child)
            if kind is None:
                walk(child)
            else:
                regions.append((child, kind))

    walk(body)
    return regions


def classify(element: HtmlElement) -> RegionKind | None:
    tag = element.tag
    if tag in NEVER_REGIONS:
        return None
    if _is_junk(element):
        return RegionKind.JUNK
    if _is_chrome(element):
        return RegionKind.CHROME
    return None


def collapse(element: HtmlElement) -> None:
    placeholder = element.makeelement(element.tag, {"data-collapsed": summarize(element)})
    placeholder.tail = element.tail
    parent = element.getparent()
    if parent is not None:
        parent.replace(element, placeholder)


def summarize(element: HtmlElement) -> str:
    links = sum(1 for _ in element.iter("a"))
    words = len(normalized_text(element).split())
    return f"{links} links, {words} words"


def _is_junk(element: HtmlElement) -> bool:
    names = f"{element.get('class') or ''} {element.get('id') or ''}".lower()
    return any(token in JUNK_TOKENS for token in _TOKEN_SPLIT.split(names) if token)


def _is_chrome(element: HtmlElement) -> bool:
    tag = element.tag
    if tag in ("header", "footer") and _inside_content(element):
        return False
    if tag in CHROME_TAGS or (element.get("role") or "").lower() in CHROME_ROLES:
        return True
    return tag in LINK_DENSITY_TAGS and _is_link_dense(element)


def _inside_content(element: HtmlElement) -> bool:
    return any(
        ancestor.tag in CONTENT_CONTAINERS or _is_role_main(ancestor)
        for ancestor in element.iterancestors()
    )


def _main_content_anchors(body: HtmlElement) -> list[HtmlElement]:
    """The elements find_main_content would pick first: main elements, else a lone article."""
    mains = [
        element
        for element in body.iter()
        if isinstance(element.tag, str) and (element.tag == "main" or _is_role_main(element))
    ]
    if mains:
        return mains
    articles = list(body.iter("article"))
    return articles if len(articles) == 1 else []


def _is_role_main(element: HtmlElement) -> bool:
    return (element.get("role") or "").lower() == "main"


def _is_link_dense(element: HtmlElement) -> bool:
    links = list(element.iter("a"))
    if len(links) < MIN_LINKS_FOR_DENSITY:
        return False
    total = len(normalized_text(element))
    link_texts = [normalized_text(link) for link in links]
    linked = sum(len(text) for text in link_texts)
    average_words = sum(len(text.split()) for text in link_texts) / len(links)
    return (
        total > 0
        and linked / total > LINK_DENSITY_THRESHOLD
        and average_words < MAX_AVERAGE_WORDS_PER_NAV_LINK
    )
