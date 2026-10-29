from prellm.report import format_size, image_tokens, report_line, text_tokens


def test_text_tokens_round_up() -> None:
    assert text_tokens(0) == 0
    assert text_tokens(9) == 3


def test_image_tokens_use_anthropic_formula() -> None:
    assert image_tokens(725, 1568) == 1516


def test_format_size() -> None:
    assert format_size(812) == "812 B"
    assert format_size(421_888) == "412.0 KB"
    assert format_size(3 * 1024 * 1024) == "3.0 MB"


def test_report_line() -> None:
    line = report_line("a/home.png", "out/a/home.jpg", 421_888, 39_014, 3950, 1516)
    assert line == "a/home.png -> out/a/home.jpg  412.0 KB -> 38.1 KB  ~3950 -> ~1516 tokens"
