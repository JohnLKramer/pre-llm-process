from enum import StrEnum

from lxml.html import HtmlElement

from prellm.html.parse import normalized_text

TEXT_BLOCK_TAGS = frozenset(
    {"p", "pre", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "dl", "table"}
)
CANDIDATE_TAGS = frozenset({"body", "div", "section", "article", "main", "td"})


class Strategy(StrEnum):
    MAIN = "main element"
    ARTICLE = "single article element"
    SCORE = "highest text score"


def find_main_content(body: HtmlElement) -> tuple[HtmlElement, Strategy]:
    mains = body.xpath("descendant-or-self::main | descendant-or-self::*[@role='main']")
    if len(mains) == 1:
        return mains[0], Strategy.MAIN
    articles = body.xpath("descendant-or-self::article")
    if len(articles) == 1:
        return articles[0], Strategy.ARTICLE
    return _highest_score(body), Strategy.SCORE


def text_score(element: HtmlElement) -> int:
    """Non-link text held directly by this element: its own text plus its direct text blocks."""
    score = len((element.text or "").strip())
    for child in element:
        score += len((child.tail or "").strip())
        if child.tag in TEXT_BLOCK_TAGS or (child.tag == "div" and not _has_block_child(child)):
            score += non_link_text_length(child)
    return score


def non_link_text_length(element: HtmlElement) -> int:
    linked = sum(len(normalized_text(link)) for link in element.iter("a"))
    return max(0, len(normalized_text(element)) - linked)


def _highest_score(body: HtmlElement) -> HtmlElement:
    best, best_score = body, text_score(body)
    for element in body.iter(*CANDIDATE_TAGS):
        score = text_score(element)
        if score > best_score:
            best, best_score = element, score
    return best


def _has_block_child(element: HtmlElement) -> bool:
    return any(child.tag in TEXT_BLOCK_TAGS or child.tag == "div" for child in element)
