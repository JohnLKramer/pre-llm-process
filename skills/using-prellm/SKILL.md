---
name: using-prellm
description: Use when you need to read or answer questions about a saved web page (.html/.htm), a screenshot, or another image (PNG, JPEG, GIF, TIFF, SVG) that is large or full of markup, scripts, ads, and navigation. Also use when an HTML file is too big to read whole, or when you would otherwise grep or parse raw HTML to find its content.
---

# Using prellm

## Overview

`prellm` turns a saved web page or an image into a much smaller file that keeps what you need. Saved pages typically shrink 100–800× in tokens, and screenshots shrink about 20× while staying readable. Pick the format and detail level from your objective, read the output, and re-run at a higher level only if the output tells you something is missing.

Read the original file instead when you need the raw markup itself (scripts, attributes, `<head>` metadata), exact pixels, or when the file is already small (under about 20 KB).

## Running it

No install step is needed. `uvx` fetches and caches it from GitHub (the first run needs network access):

```bash
OUT=$(mktemp -d)
uvx --from git+https://github.com/JohnLKramer/pre-llm-process prellm INPUT... --format FORMAT --detail LEVEL --out "$OUT"
```

Always write to a fresh `mktemp -d` folder, so you never read stale output from an earlier run. Each run prints a report on stderr with the output path and the estimated tokens before and after. Exit code 2 means the run was rejected before converting anything, and the message says why.

## Choose format and level from the objective

| Objective | Command flags | Why |
|---|---|---|
| Find facts, numbers, or table data in a page; summarise an article | `--format md --detail low` | Main content only, tables kept, no URLs |
| Same, but you need the links | `--format md --detail medium` | Adds links and image references |
| Everything on the page as text, including navigation and footer | `--format md --detail high` | Keeps page chrome |
| Page layout, navigation menus, header and footer, how sections are arranged | `--format html --detail medium` | Navigation and footer kept in full; ads and cookie banners collapsed |
| Only the outline of the layout | `--format html --detail low` | Navigation and footer collapsed to placeholders with link and word counts |
| Element ids, classes, or roles (CSS selectors, scrapers, browser extensions, UI tests) | `--format html --detail high` | Lower levels strip `id`, `class`, and `role` |
| Read a screenshot or image | `--format image --detail minimal`, then open the output file | 640px longest edge; enough for normal UI text |

Images come out as JPEG, or PNG when the image has transparency. Text output from `md` is the smallest; `html` costs about 2–7× as much at the same level, so use it only when layout is the question.

To read text from an image as markdown instead (`--format md` on an image), `tesseract` must be installed. If the run is rejected for missing tesseract, use `--format image` instead of installing anything.

## Read the signals, then re-run if needed

| You see | It means | Do this |
|---|---|---|
| `<nav data-collapsed="42 links, 310 words"></nav>` (or any tag with `data-collapsed`) | The region was removed, not empty | Re-run one level higher if you need what was in it. In `html`, `medium` keeps navigation and footers |
| Note: `main content kept only N% of the page's text` | Markdown kept a small part of the page | Re-run with `--detail high` |
| Markdown has no navigation or footer | Below `high`, markdown keeps only the main content | Use `--detail high`, or `--format html --detail medium` for structure |
| Image text too small or blurry to read | Resolution too low | Re-run at `low` (1024px), then `medium` (1568px) |

Go up one level at a time. Each level costs roughly 2–3× the one below it.

## Reading the output

Check the token estimate in the report before reading:

- **Under about 10K tokens:** read the whole file.
- **Larger:** first run one level lower to get an outline. Then read only the parts you need, in chunks, using your file reader's offset and limit. To find a part, run `rg -n` in the shell against `$OUT`. Some editor search tools only cover the workspace and won't see temp folders.
