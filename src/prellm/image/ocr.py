import importlib.util
import shutil

from PIL import Image

from prellm.image.raster import open_first_frame
from prellm.levels import OcrSettings


def missing_ocr_prerequisites() -> list[str]:
    problems = []
    if importlib.util.find_spec("pytesseract") is None:
        problems.append("OCR needs the pytesseract package: run `uv sync --extra ocr`")
    if shutil.which("tesseract") is None:
        problems.append("OCR needs the tesseract binary on PATH: run `brew install tesseract`")
    return problems


def ocr_to_markdown(data: bytes, settings: OcrSettings) -> tuple[str, int]:
    """Return markdown paragraphs in Tesseract's reading order, and how many frames were dropped."""
    import pytesseract

    frame, frames_dropped = open_first_frame(data)
    frame = frame.convert("RGB")
    if settings.upscale > 1:
        size = (frame.width * settings.upscale, frame.height * settings.upscale)
        frame = frame.resize(size, Image.Resampling.LANCZOS)
    words = pytesseract.image_to_data(frame, output_type=pytesseract.Output.DICT)

    paragraphs: dict[tuple[int, int], list[str]] = {}
    for index, word in enumerate(words["text"]):
        if not word.strip() or float(words["conf"][index]) < settings.min_confidence:
            continue
        key = (int(words["block_num"][index]), int(words["par_num"][index]))
        paragraphs.setdefault(key, []).append(word.strip())

    text = "\n\n".join(" ".join(paragraph) for paragraph in paragraphs.values())
    return (text + "\n" if text else ""), frames_dropped
