from dataclasses import dataclass

from prellm.html.chrome import RegionKind, collapse, find_regions
from prellm.html.clean import clean_always
from prellm.html.content import find_main_content
from prellm.html.markdown import to_markdown
from prellm.html.parse import body_of, normalized_text, parse_html
from prellm.html.serialize import apply_html_settings, serialize
from prellm.levels import HtmlSettings, MarkdownSettings

LOW_CONTENT_RATIO = 0.1


@dataclass(frozen=True)
class HtmlResult:
    text: str
    notices: tuple[str, ...]


def html_to_markdown(data: bytes, settings: MarkdownSettings) -> HtmlResult:
    root = parse_html(data)
    clean_always(root)
    body = body_of(root)
    page_length = len(normalized_text(body))
    for region, kind in find_regions(body):
        if kind is RegionKind.JUNK or settings.main_content_only:
            region.drop_tree()
    if not settings.main_content_only:
        return HtmlResult(text=to_markdown(body, settings), notices=())

    content, strategy = find_main_content(body)
    notices = [f"main content found by: {strategy}"]
    content_length = len(normalized_text(content))
    if page_length and content_length < LOW_CONTENT_RATIO * page_length:
        percent = round(100 * content_length / page_length)
        notices.append(
            f"main content kept only {percent}% of the page's text; "
            "re-run with --detail high to keep the whole page"
        )
    return HtmlResult(text=to_markdown(content, settings), notices=tuple(notices))


def html_to_html(data: bytes, settings: HtmlSettings) -> HtmlResult:
    root = parse_html(data)
    clean_always(root)
    body = body_of(root)
    for region, kind in find_regions(body):
        if (kind is RegionKind.JUNK and settings.collapse_junk) or (
            kind is RegionKind.CHROME and settings.collapse_chrome
        ):
            collapse(region)
    apply_html_settings(root, body, settings)
    return HtmlResult(text=serialize(root), notices=())
