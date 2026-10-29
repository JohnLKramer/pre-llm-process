import io
import shutil
from pathlib import Path

import pytest
from builders import FIXTURES, screenshot_png
from PIL import Image

from prellm.cli import EXIT_FAILED, EXIT_OK, EXIT_REJECTED, main


@pytest.fixture
def inputs(tmp_path: Path) -> Path:
    root = tmp_path / "in"
    (root / "app").mkdir(parents=True)
    (root / "app" / "home.png").write_bytes(screenshot_png(600, 1200))
    (root / "app" / "notes.txt").write_text("ignored")
    shutil.copy(FIXTURES / "article.html", root / "article.html")
    shutil.copy(FIXTURES / "inkscape.svg", root / "badge.svg")
    return root


def test_directory_mirrors_into_out(
    inputs: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out"
    assert main([str(inputs), "--out", str(out), "--detail", "low"]) == EXIT_OK
    written = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file())
    assert written == ["app/home.jpg", "article.md", "badge.png"]
    assert Image.open(out / "app" / "home.jpg").size == (512, 1024)
    report = capsys.readouterr().err
    assert f"app/home.png -> {out / 'app' / 'home.jpg'}" in report
    assert "note: main content found by: main element" in report


def test_single_text_input_goes_to_stdout(inputs: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(inputs / "article.html"), "--format", "html"]) == EXIT_OK
    captured = capsys.readouterr()
    assert captured.out.startswith("<!DOCTYPE html>")
    assert "-> stdout" in captured.err


def test_format_applies_to_every_input(inputs: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    assert main([str(inputs / "badge.svg"), "--format", "svg", "--out", str(out)]) == EXIT_OK
    assert (out / "badge.svg").read_text().startswith("<svg")


def test_rejects_unsupported_format_before_writing(
    inputs: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out"
    assert main([str(inputs), "--format", "html", "--out", str(out)]) == EXIT_REJECTED
    assert not out.exists()
    err = capsys.readouterr().err
    assert "home.png: --format html is not supported for raster image (image, md)" in err
    assert "badge.svg: --format html is not supported for svg (image, svg)" in err


def test_rejects_collisions(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "home.png").write_bytes(screenshot_png(10, 10))
    (tmp_path / "home.jpg").write_bytes(screenshot_png(10, 10))
    assert main([str(tmp_path), "--out", str(tmp_path / "out")]) == EXIT_REJECTED
    assert "would both write" in capsys.readouterr().err


def test_rejects_overwriting_an_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "badge.svg"
    source.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>')
    original = source.read_bytes()
    assert main([str(tmp_path), "--format", "svg", "--out", str(tmp_path)]) == EXIT_REJECTED
    assert "would overwrite its input" in capsys.readouterr().err
    assert source.read_bytes() == original


def test_rejects_image_output_and_multiple_inputs_without_out(
    inputs: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(inputs / "app" / "home.png")]) == EXIT_REJECTED
    assert "image output needs --out DIR" in capsys.readouterr().err
    assert main([str(inputs)]) == EXIT_REJECTED
    assert "more than one input needs --out DIR" in capsys.readouterr().err


def test_rejects_missing_and_unsupported_inputs(
    inputs: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main([str(inputs / "nope.png"), str(inputs / "app" / "notes.txt")])
    assert code == EXIT_REJECTED
    err = capsys.readouterr().err
    assert "nope.png: no such file or directory" in err
    assert "notes.txt: unsupported file type '.txt'" in err


def test_rejects_directory_with_nothing_to_convert(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path), "--out", str(tmp_path / "out")]) == EXIT_REJECTED
    assert "no supported input files found" in capsys.readouterr().err


def test_ocr_without_tesseract_is_rejected(
    inputs: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    code = main([str(inputs / "app" / "home.png"), "--format", "md", "--out", str(tmp_path / "o")])
    assert code == EXIT_REJECTED
    assert "brew install tesseract" in capsys.readouterr().err


def test_corrupt_file_stops_the_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "a.png").write_bytes(screenshot_png(10, 10))
    (tmp_path / "b.png").write_bytes(b"garbage")
    out = tmp_path / "out"
    assert main([str(tmp_path), "--out", str(out)]) == EXIT_FAILED
    err = capsys.readouterr().err
    assert "b.png: UnidentifiedImageError" in err
    assert (out / "a.jpg").exists()


def test_jpeg_output_is_valid(inputs: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    main([str(inputs / "app" / "home.png"), "--out", str(out), "--detail", "high"])
    image = Image.open(io.BytesIO((out / "home.jpg").read_bytes()))
    assert image.format == "JPEG"
    assert image.size == (600, 1200)


def test_dotted_filename_keeps_its_dots(tmp_path: Path) -> None:
    source = tmp_path / "shot.v2.png"
    source.write_bytes(screenshot_png(10, 10))
    out = tmp_path / "out"
    assert main([str(source), "--out", str(out)]) == EXIT_OK
    assert [p.name for p in out.iterdir()] == ["shot.v2.jpg"]


def test_rejects_rewriting_an_input_image(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "x.jpg"
    source.write_bytes(screenshot_png(10, 10))
    original = source.read_bytes()
    assert main([str(tmp_path), "--out", str(tmp_path)]) == EXIT_REJECTED
    assert "x.jpg would overwrite its input" in capsys.readouterr().err
    assert source.read_bytes() == original


def test_rejects_png_input_that_would_be_rewritten_as_jpg(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "x.png").write_bytes(screenshot_png(10, 10))
    (tmp_path / "x.jpg").write_bytes(screenshot_png(10, 10))
    assert (
        main([str(tmp_path / "x.png"), str(tmp_path / "x.jpg"), "--out", str(tmp_path)])
        == EXIT_REJECTED
    )
    assert "would overwrite its input" in capsys.readouterr().err
