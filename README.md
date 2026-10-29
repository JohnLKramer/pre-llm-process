# pre-llm-process

Screenshots and web pages cost a lot of tokens, and most of those tokens are noise. `prellm`
shrinks images and HTML pages into smaller files an LLM can read for far fewer tokens. You pick
the output format and how much detail to keep, and you can re-run at a different level if the
result has too much or too little.

Don't use it when you need a file's raw markup, scripts, or metadata. Read the original instead.

- [Install](#install)
- [Using it from an agent](#using-it-from-an-agent)
- [Usage](#usage)
- [Detail levels](#detail-levels)
- [Results](#results)
- [Exit codes](#exit-codes)
- [Development](#development)

## Install

```bash
uv sync                 # images, SVG, and HTML
uv sync --extra ocr     # also OCR of images to markdown
brew install tesseract  # OCR also needs the tesseract binary
```

## Using it from an agent

`skills/using-prellm/` is an agent skill. It tells an agent when to use `prellm` and which
format and level fit its objective, and it runs the tool straight from GitHub with `uvx`, so
there is nothing to install besides `uv`. To install it, copy or symlink the folder into your
agent's skills directory:

```bash
git clone https://github.com/JohnLKramer/pre-llm-process
ln -s "$PWD/pre-llm-process/skills/using-prellm" ~/.agents/skills/using-prellm
```

`~/.agents/skills/` is read by Claude Code, Codex, Copilot CLI, and Gemini CLI. Use
`~/.claude/skills/` or `~/.cursor/skills/` if your agent only reads its own folder.

## Usage

```bash
prellm INPUT... [--format md|html|image|svg] [--detail minimal|low|medium|high] [--out DIR]
```

- `INPUT` is any number of files or directories. Directories are searched recursively for
  `.html`, `.htm`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.tif`, `.tiff`, and `.svg`.
- `--out DIR` mirrors input paths: `prellm shots/ --out out/` writes `shots/a/home.png` to
  `out/a/home.jpg`. Without `--out`, a single text result goes to stdout. Image output always
  needs `--out`.
- A report on stderr shows each file's size and estimated tokens before and after.

| Input | Formats (default first) |
|---|---|
| HTML | `md` (text only), `html` (keeps layout) |
| PNG, JPEG, GIF, TIFF | `image`, `md` (OCR) |
| SVG | `image` (rasterized), `svg` (minified) |

Use `md` when you only need the text and `html` when layout matters.

Image output is JPEG, or PNG when the image has transparent pixels, so any image reader can open
it. Metadata is stripped and only the first frame of an animation or multi-page file is kept.

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

## Results

These are one-off measurements on five real inputs, each run once at every level. They show the
size of the effect, not a benchmark.

The inputs are a saved CNN homepage (7.3 MB), a saved ESPN fantasy-football roster page (1.1 MB),
and three phone screenshots of social-media posts (390–520 KB each). Token counts are the
estimates from `prellm`'s report: characters ÷ 4 for text, and width × height ÷ 750 for images.
The number in brackets is how many times smaller the output is.

| Input | Format | minimal | low | medium | high |
|---|---|---|---|---|---|
| CNN, ~1.9M tokens | `md` | 2.3K (830×) | 3.5K (540×) | 8.4K (230×) | 14K (140×) |
| | `html` | 6.7K (290×) | 13K (140×) | 25K (76×) | 73K (26×) |
| ESPN, ~298K tokens | `md` | 1.1K (260×) | 1.1K (260×) | 1.2K (255×) | 3.8K (78×) |
| | `html` | 2.1K (145×) | 3.8K (78×) | 8.3K (36×) | 28K (10×) |
| Screenshot, ~5K tokens each | `image` | 252 (20×) | 644 (8×) | 1.5K (3.3×) | 5K (1×) |

What the numbers mean:

- Most of a saved HTML page is scripts, styles, inline SVG, and tracking markup. Removing that
  accounts for most of the reduction, even at `high`. The "before" figure is the cost of pasting
  the raw file, so it's the worst case.
- ESPN's markdown barely grows from `minimal` to `medium`, because its main content is one roster
  table. At `high`, navigation and page chrome come back.
- `html` costs about 2–7 times as much as `md` at the same level. Use it only when layout matters.
- Screenshots stay readable at `minimal` (640px longest edge). At `high`, the pixel count and
  token estimate stay the same, and the JPEG is only 1.1–1.35 times smaller in bytes than the
  original PNG. Use `high` only when fine detail matters.
- Many model providers downscale large images themselves before counting tokens. The real saving
  on screenshots compared with uploading the original is therefore smaller than the table shows,
  especially at `medium` and `high`.

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
