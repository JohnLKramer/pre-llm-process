# pre-llm-process

Screenshots and web pages cost a lot of tokens, and most of those tokens are noise. `prellm`
shrinks images and HTML pages into smaller files an LLM can read for far fewer tokens. You pick
the output format and how much detail to keep, and you can re-run at a different level if the
result has too much or too little.

Don't use it when you need a file's raw markup, scripts, or metadata. Read the original instead.

- [Install](#install)
- [Usage](#usage)
- [Detail levels](#detail-levels)
- [Exit codes](#exit-codes)
- [Development](#development)

## Install

```bash
uv sync                 # images, SVG, and HTML
uv sync --extra ocr     # also OCR of images to markdown
brew install tesseract  # OCR also needs the tesseract binary
```

## Usage

```bash
prellm INPUT... [--format md|html|image|svg] [--detail minimal|low|medium|high] [--out DIR]
```

- `INPUT` is any number of files or directories. Directories are searched recursively for
  `.html`, `.htm`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.tif`, `.tiff`, and `.svg`.
- `--out DIR` mirrors input paths: `prellm shots/ --out out/` writes `shots/a/home.png` to
  `out/a/home.webp`. Without `--out`, a single text result goes to stdout. Image output always
  needs `--out`.
- A report on stderr shows each file's size and estimated tokens before and after.

| Input | Formats (default first) |
|---|---|
| HTML | `md` (text only), `html` (keeps layout) |
| PNG, JPEG, GIF, TIFF | `image` (WebP), `md` (OCR) |
| SVG | `image` (rasterized WebP), `svg` (minified) |

Use `md` when you only need the text and `html` when layout matters.

## Detail levels

The default is `medium`.

| Level | Images | Markdown from HTML | HTML from HTML |
|---|---|---|---|
| `minimal` | longest edge 640px, quality 60 | main content, no links or images | navigation and junk collapsed to placeholders, structural tags only, no attributes (keeps `<br>` and `<hr>`) |
| `low` | 1024px, quality 75 | main content, image alt text, no URLs | navigation and junk collapsed, image alt text, `href` only |
| `medium` | 1568px, quality 85 | main content, links, images | full page structure, junk collapsed, layout attributes |
| `high` | original size, quality 90 | whole page including navigation | nothing collapsed, extra attributes (`id`, `class`, `role`, `aria-label`) |

Higher levels also keep more OCR text (lower confidence cutoff) and more SVG coordinate
precision.

A collapsed region looks like `<nav data-collapsed="42 links, 310 words"></nav>`, so you can
see what was removed and re-run at a higher level if you need it.

## Exit codes

- `0`: every file converted.
- `1`: a file failed to convert. The error names the file. Files already written are kept.
- `2`: the run was rejected before converting anything, for example a missing input, an
  unsupported format, two inputs that would write the same output, or an output that would
  overwrite one of the inputs. Every problem is listed.

## Development

```bash
uv sync --extra ocr
uv run ruff format
uv run ruff check --fix
uv run mypy src/
uv run pytest
```

`tests/test_snapshots.py` converts the real pages in `tests/fixtures/pages/` at every detail level
and format, and compares the output with the files in `tests/snapshots/`. After a change that is
meant to alter the output, regenerate the snapshots with
`UPDATE_SNAPSHOTS=1 uv run pytest tests/test_snapshots.py` and review the diff before committing.
