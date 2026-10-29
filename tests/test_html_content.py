from prellm.html.content import Strategy, find_main_content
from prellm.html.parse import body_of, parse_html


def main_content(html: str) -> tuple[str, Strategy]:
    body = body_of(parse_html(html.encode("utf-8")))
    element, strategy = find_main_content(body)
    return element.get("id") or element.tag, strategy


def test_prefers_single_main_element() -> None:
    html = '<body><main id="m"><p>a</p></main><article id="x"><p>b</p></article></body>'
    assert main_content(html) == ("m", Strategy.MAIN)


def test_role_main_counts_as_main() -> None:
    assert main_content('<body><div id="m" role="main"><p>a</p></div></body>') == (
        "m",
        Strategy.MAIN,
    )


def test_single_article_when_no_main() -> None:
    assert main_content('<body><div><article id="a"><p>a</p></article></div></body>') == (
        "a",
        Strategy.ARTICLE,
    )


def test_multiple_articles_fall_back_to_score() -> None:
    html = (
        '<body><div id="feed"><article><p>one</p></article><article><p>two</p></article></div>'
        f'<div id="story"><p>{"long text " * 50}</p><p>{"more " * 50}</p></div></body>'
    )
    assert main_content(html) == ("story", Strategy.SCORE)


def test_score_ignores_link_text() -> None:
    links = " ".join(f'<a href="/{i}">a very long link title number {i}</a>' for i in range(20))
    html = f'<body><div id="links"><p>{links}</p></div><div id="text"><p>{"word " * 40}</p></div></body>'
    assert main_content(html) == ("text", Strategy.SCORE)


def test_score_counts_div_paragraphs() -> None:
    html = f'<body><div id="post"><div>{"line one " * 30}</div><div>{"line two " * 30}</div></div></body>'
    assert main_content(html) == ("post", Strategy.SCORE)
