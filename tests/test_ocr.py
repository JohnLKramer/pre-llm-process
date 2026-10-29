import io
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

from prellm.image.ocr import missing_ocr_prerequisites, ocr_to_markdown
from prellm.levels import Detail, ocr_settings

needs_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None or bool(missing_ocr_prerequisites()),
    reason="OCR tests need `uv sync --extra ocr` and `brew install tesseract`",
)


def text_image(lines: list[str]) -> bytes:
    image = Image.new("RGB", (900, 120 * len(lines) + 80), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=48)
    for index, line in enumerate(lines):
        draw.text((40, 40 + index * 120), line, fill="black", font=font)
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def test_missing_prerequisites_are_named(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    problems = missing_ocr_prerequisites()
    assert any("brew install tesseract" in problem for problem in problems)


@needs_tesseract
@pytest.mark.parametrize("detail", list(Detail))
def test_ocr_reads_clear_text(detail: Detail) -> None:
    text, frames_dropped = ocr_to_markdown(text_image(["Order history"]), ocr_settings(detail))
    assert "Order history" in text
    assert frames_dropped == 0


@needs_tesseract
def test_blank_image_produces_empty_markdown() -> None:
    text, _ = ocr_to_markdown(text_image([]), ocr_settings(Detail.HIGH))
    assert text == ""
