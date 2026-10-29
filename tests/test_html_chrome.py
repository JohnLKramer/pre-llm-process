import lxml.html

from prellm.html.chrome import RegionKind, collapse, find_regions
from prellm.html.parse import body_of, parse_html


def regions(html: str) -> list[tuple[str, RegionKind]]:
    body = body_of(parse_html(html.encode("utf-8")))
    return [(element.get("id") or element.tag, kind) for element, kind in find_regions(body)]


def test_semantic_chrome_tags_and_roles() -> None:
    found = regions(
        "<body><header>h</header><nav>n</nav><aside>a</aside><footer>f</footer>"
        '<div id="r" role="navigation">r</div><p>text</p></body>'
    )
    assert found == [
        ("header", RegionKind.CHROME),
        ("nav", RegionKind.CHROME),
        ("aside", RegionKind.CHROME),
        ("footer", RegionKind.CHROME),
        ("r", RegionKind.CHROME),
    ]


def test_header_and_footer_inside_article_are_content() -> None:
    found = regions(
        "<body><article><header><h1>T</h1></header><p>x</p><footer>by me</footer></article></body>"
    )
    assert found == []


def test_link_dense_block_is_chrome() -> None:
    links = "".join(f'<a href="/{i}">Link {i}</a>' for i in range(5))
    found = regions(
        f'<body><div id="menu">{links}</div><div id="text">{links}<p>{"words " * 100}</p></div></body>'
    )
    assert found == [("menu", RegionKind.CHROME)]


def test_headline_lists_are_content_not_chrome() -> None:
    headlines = "".join(
        f'<a href="/{i}">Officials announce new plan for city transit number {i}</a>'
        for i in range(8)
    )
    assert regions(f'<body><div id="stories">{headlines}</div></body>') == []


def test_fewer_than_five_links_is_not_link_dense() -> None:
    links = "".join(f'<a href="/{i}">Link {i}</a>' for i in range(4))
    assert regions(f'<body><div id="menu">{links}</div></body>') == []


def test_junk_matches_whole_class_tokens() -> None:
    found = regions(
        '<body><div id="cookie-banner">c</div><div class="ad-slot">a</div>'
        '<div class="share_buttons">s</div><div id="x" class="header-loader download">ok</div></body>'
    )
    assert found == [
        ("cookie-banner", RegionKind.JUNK),
        ("div", RegionKind.JUNK),
        ("div", RegionKind.JUNK),
    ]


def test_body_and_main_are_never_regions() -> None:
    assert regions('<body class="modal-open"><main class="social"><p>x</p></main></body>') == []


def test_wrappers_around_main_content_are_not_regions() -> None:
    found = regions(
        '<body><div id="w" class="modal-open"><nav id="n">n</nav><main><p>x</p></main></div>'
        '<div id="r" class="share"><div role="main"><p>y</p></div></div></body>'
    )
    assert found == [("n", RegionKind.CHROME)]


def test_wrapper_around_a_single_article_is_not_a_region() -> None:
    found = regions('<body><div id="w" class="share-page"><article><p>x</p></article></div></body>')
    assert found == []


def test_wrappers_around_one_of_many_articles_can_be_regions() -> None:
    found = regions(
        '<body><div id="a" class="share"><article><p>x</p></article></div>'
        "<article><p>y</p></article></body>"
    )
    assert found == [("a", RegionKind.JUNK)]


def test_header_inside_role_main_is_content() -> None:
    assert regions('<body><div role="main"><header><h1>T</h1></header><p>x</p></div></body>') == []


def test_regions_are_outermost_only() -> None:
    assert regions("<body><header><nav>n</nav></header></body>") == [("header", RegionKind.CHROME)]


def test_collapse_leaves_a_summary_placeholder() -> None:
    body = body_of(
        parse_html(b'<body><nav><a href="/a">Home page</a> <a href="/b">Shop</a></nav>tail</body>')
    )
    ((nav, _),) = find_regions(body)
    collapse(nav)
    html = lxml.html.tostring(body, encoding="unicode")
    assert html == '<body><nav data-collapsed="2 links, 3 words"></nav>tail</body>'
