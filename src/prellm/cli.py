import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from prellm import report
from prellm.convert import convert
from prellm.formats import (
    ALLOWED_FORMATS,
    OUTPUT_EXTENSIONS,
    InputKind,
    OutputFormat,
    default_format,
    input_kind,
)
from prellm.image.ocr import missing_ocr_prerequisites
from prellm.levels import Detail

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REJECTED = 2


@dataclass(frozen=True)
class Job:
    source: Path
    kind: InputKind
    fmt: OutputFormat
    destination: Path | None


def plan_jobs(
    inputs: list[Path], fmt: OutputFormat | None, out: Path | None
) -> tuple[list[Job], list[str]]:
    """Expand inputs into jobs and collect every reason the run cannot start."""
    problems: list[str] = []
    found: list[tuple[Path, InputKind, Path]] = []
    for argument in inputs:
        if argument.is_dir():
            for path in sorted(p for p in argument.rglob("*") if p.is_file()):
                kind = input_kind(path)
                if kind is not None:
                    found.append((path, kind, path.relative_to(argument)))
        elif argument.is_file():
            kind = input_kind(argument)
            if kind is None:
                problems.append(f"{argument}: unsupported file type {argument.suffix!r}")
            else:
                found.append((argument, kind, Path(argument.name)))
        else:
            problems.append(f"{argument}: no such file or directory")

    if not found and not problems:
        problems.append("no supported input files found")

    jobs: list[Job] = []
    for source, kind, relative in found:
        chosen = fmt or default_format(kind)
        if chosen not in ALLOWED_FORMATS[kind]:
            allowed = ", ".join(ALLOWED_FORMATS[kind])
            problems.append(f"{source}: --format {chosen} is not supported for {kind} ({allowed})")
            continue
        destination = None
        if out is not None:
            destination = out / relative.with_suffix(OUTPUT_EXTENSIONS[chosen])
        jobs.append(Job(source, kind, chosen, destination))

    if out is None:
        if len(found) > 1:
            problems.append("more than one input needs --out DIR")
        problems.extend(
            f"{job.source}: image output needs --out DIR"
            for job in jobs
            if job.fmt is OutputFormat.IMAGE
        )

    sources = {source.resolve() for source, _, _ in found}
    claimed: dict[Path, Path] = {}
    for job in jobs:
        if job.destination is None:
            continue
        if job.destination.resolve() in sources:
            problems.append(f"{job.source}: {job.destination} would overwrite its input")
        elif job.destination in claimed:
            problems.append(
                f"{claimed[job.destination]} and {job.source} would both write {job.destination}"
            )
        else:
            claimed[job.destination] = job.source

    if any(job.kind is InputKind.RASTER and job.fmt is OutputFormat.MD for job in jobs):
        problems.extend(missing_ocr_prerequisites())

    return jobs, problems


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prellm",
        description="Convert images and HTML pages into smaller files for LLMs.",
    )
    parser.add_argument("inputs", nargs="+", type=Path, metavar="INPUT")
    parser.add_argument("--format", choices=[f.value for f in OutputFormat])
    parser.add_argument("--detail", choices=[d.value for d in Detail], default=Detail.MEDIUM.value)
    parser.add_argument("--out", type=Path, metavar="DIR")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fmt = OutputFormat(args.format) if args.format else None
    detail = Detail(args.detail)
    jobs, problems = plan_jobs(args.inputs, fmt, args.out)
    if problems:
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        return EXIT_REJECTED

    for job in jobs:
        data = job.source.read_bytes()
        try:
            converted = convert(data, job.kind, job.fmt, detail)
        except Exception as error:
            print(f"error: {job.source}: {type(error).__name__}: {error}", file=sys.stderr)
            return EXIT_FAILED
        if job.destination is None:
            sys.stdout.write(converted.data.decode("utf-8"))
            destination = "stdout"
        else:
            job.destination.parent.mkdir(parents=True, exist_ok=True)
            job.destination.write_bytes(converted.data)
            destination = str(job.destination)
        line = report.report_line(
            str(job.source),
            destination,
            len(data),
            len(converted.data),
            converted.source_tokens,
            converted.output_tokens,
        )
        print(line, file=sys.stderr)
        for notice in converted.notices:
            print(f"  note: {notice}", file=sys.stderr)
    return EXIT_OK
