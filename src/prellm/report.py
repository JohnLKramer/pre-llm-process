import math

CHARS_PER_TOKEN = 4
PIXELS_PER_TOKEN = 750


def text_tokens(char_count: int) -> int:
    return math.ceil(char_count / CHARS_PER_TOKEN)


def image_tokens(width: int, height: int) -> int:
    return math.ceil(width * height / PIXELS_PER_TOKEN)


def format_size(byte_count: int) -> str:
    if byte_count < 1024:
        return f"{byte_count} B"
    if byte_count < 1024 * 1024:
        return f"{byte_count / 1024:.1f} KB"
    return f"{byte_count / (1024 * 1024):.1f} MB"


def report_line(
    source: str,
    destination: str,
    source_bytes: int,
    output_bytes: int,
    source_tokens: int,
    output_tokens: int,
) -> str:
    return (
        f"{source} -> {destination}  "
        f"{format_size(source_bytes)} -> {format_size(output_bytes)}  "
        f"~{source_tokens} -> ~{output_tokens} tokens"
    )
