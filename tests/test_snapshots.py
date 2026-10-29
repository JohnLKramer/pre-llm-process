import os
from pathlib import Path

import pytest
from builders import FIXTURES

from prellm.html.pipeline import html_to_html, html_to_markdown
from prellm.levels import Detail, html_settings, markdown_settings

PAGES = sorted((FIXTURES / "pages").glob("*.html"))
SNAPSHOTS = Path(__file__).parent / "snapshots"
UPDATE = os.environ.get("UPDATE_SNAPSHOTS") == "1"


def render(page: Path, detail: Detail, fmt: str) -> str:
    data = page.read_bytes()
    if fmt == "md":
        return html_to_markdown(data, markdown_settings(detail)).text
    return html_to_html(data, html_settings(detail)).text


@pytest.mark.parametrize("fmt", ["md", "html"])
@pytest.mark.parametrize("detail", list(Detail))
@pytest.mark.parametrize("page", PAGES, ids=[page.stem for page in PAGES])
def test_real_page_matches_snapshot(page: Path, detail: Detail, fmt: str) -> None:
    actual = render(page, detail, fmt)
    snapshot = SNAPSHOTS / f"{page.stem}.{detail}.{fmt}"
    if UPDATE:
        snapshot.parent.mkdir(exist_ok=True)
        snapshot.write_text(actual)
    assert snapshot.exists(), f"missing {snapshot}; run with UPDATE_SNAPSHOTS=1 and review the diff"
    assert actual == snapshot.read_text()


@pytest.mark.parametrize("fmt", ["md", "html"])
@pytest.mark.parametrize("page", PAGES, ids=[page.stem for page in PAGES])
def test_real_page_output_grows_with_detail(page: Path, fmt: str) -> None:
    sizes = [len(render(page, detail, fmt)) for detail in Detail]
    assert sizes == sorted(sizes)
