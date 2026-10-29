import re

import resvg_py
from lxml import etree

from prellm.image.raster import RasterResult, convert_raster
from prellm.levels import RasterSettings, SvgSettings

EDITOR_NAMESPACES = frozenset(
    {
        "http://www.inkscape.org/namespaces/inkscape",
        "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
        "http://ns.adobe.com/AdobeIllustrator/10.0/",
        "http://ns.adobe.com/AdobeSVGViewerExtensions/3.0/",
        "http://ns.adobe.com/Extensibility/1.0/",
        "http://ns.adobe.com/Flows/1.0/",
        "http://ns.adobe.com/GenericCustomNamespace/1.0/",
        "http://ns.adobe.com/Graphs/1.0/",
        "http://ns.adobe.com/ImageReplacement/1.0/",
        "http://ns.adobe.com/SaveForWeb/1.0/",
        "http://ns.adobe.com/Variables/1.0/",
        "http://ns.adobe.com/XPath/1.0/",
        "http://www.bohemiancoding.com/sketch/ns",
    }
)

# transform is excluded: rounding rotation and scale factors distorts the drawing.
COORDINATE_ATTRIBUTES = frozenset(
    {
        "d", "points", "viewBox", "x", "y", "x1", "y1", "x2", "y2",
        "cx", "cy", "r", "rx", "ry", "fx", "fy", "dx", "dy", "width", "height",
    }
)  # fmt: skip

TEXT_ELEMENTS = frozenset({"text", "tspan", "textPath", "title", "desc", "style"})

_NUMBER = re.compile(r"-?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")
_LENGTH = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:px)?\s*$")


class SvgSizeError(ValueError):
    pass


def rasterize_svg(data: bytes, settings: RasterSettings) -> RasterResult:
    intrinsic_size(_parse(data))
    png = resvg_py.svg_to_bytes(svg_string=data.decode("utf-8"))
    return convert_raster(bytes(png), settings)


def intrinsic_size(root: etree._Element) -> tuple[float, float]:
    width = _length(root.get("width"))
    height = _length(root.get("height"))
    if width is not None and height is not None:
        return width, height
    view_box = root.get("viewBox")
    if view_box:
        parts = view_box.replace(",", " ").split()
        if len(parts) == 4:
            try:
                width, height = float(parts[2]), float(parts[3])
            except ValueError:
                raise SvgSizeError(f"SVG viewBox {view_box!r} is not four numbers") from None
            if width <= 0 or height <= 0:
                raise SvgSizeError(f"SVG viewBox {view_box!r} must have positive width and height")
            return width, height
    raise SvgSizeError("SVG has no numeric width/height and no viewBox, so it has no size")


def minify_svg(data: bytes, settings: SvgSettings) -> str:
    root = _parse(data)
    for node in list(root.iter(etree.Comment, etree.ProcessingInstruction)):
        _remove(node)
    for element in list(root.iter()):
        if _namespace(element.tag) in EDITOR_NAMESPACES or _local(element.tag) == "metadata":
            _remove(element)
    for element in root.iter():
        for name in list(element.attrib):
            if _namespace(name) in EDITOR_NAMESPACES:
                del element.attrib[name]
            elif settings.decimals is not None and name in COORDINATE_ATTRIBUTES:
                round_value = round_path if name == "d" else round_numbers
                element.set(name, round_value(element.get(name), settings.decimals))
    for element in reversed(list(root.iter())):
        if _local(element.tag) == "g" and len(element) == 0 and not (element.text or "").strip():
            _remove(element)
    for element in root.iter():
        if _local(element.tag) in TEXT_ELEMENTS:
            continue
        if element.text is not None and not element.text.strip():
            element.text = None
        for child in element:
            if child.tail is not None and not child.tail.strip():
                child.tail = None
    etree.cleanup_namespaces(root)
    result: str = etree.tostring(root, encoding="unicode")
    return result + "\n"


def round_numbers(value: str, decimals: int) -> str:
    def replace(match: re.Match[str]) -> str:
        text = _format_number(match.group(), decimals)
        start = match.start()
        needs_space = start > 0 and value[start - 1] in "0123456789." and not text.startswith("-")
        return " " + text if needs_space else text

    return _NUMBER.sub(replace, value)


def round_path(value: str, decimals: int) -> str:
    """Round path data; arc flags are single 0/1 characters and may touch the next number."""
    out: list[str] = []
    command = ""
    index = 0  # parameters read since the last command letter
    pos = 0
    while True:
        while pos < len(value) and value[pos] in " \t\r\n,":
            pos += 1
        if pos >= len(value):
            return "".join(out)
        char = value[pos]
        if char.isalpha():
            command, index = char, 0
            out.append(char)
            pos += 1
            continue
        if command in ("A", "a") and index % 7 in (3, 4):
            if char not in "01":
                raise ValueError(f"Invalid arc flag {char!r} in path data {value!r}")
            token, pos = char, pos + 1
        else:
            match = _NUMBER.match(value, pos)
            if match is None:
                raise ValueError(f"Unexpected {char!r} in path data {value!r}")
            token, pos = _format_number(match.group(), decimals), match.end()
        if out and not out[-1].isalpha():
            out.append(" ")
        out.append(token)
        index += 1


def _format_number(raw: str, decimals: int) -> str:
    text = f"{round(float(raw), decimals):.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def _parse(data: bytes) -> etree._Element:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, remove_blank_text=False)
    root: etree._Element = etree.fromstring(data, parser)
    return root


def _length(value: str | None) -> float | None:
    if value is None:
        return None
    match = _LENGTH.match(value)
    return float(match.group(1)) if match else None


def _namespace(name: object) -> str | None:
    if isinstance(name, str) and name.startswith("{"):
        return name[1:].split("}", 1)[0]
    return None


def _local(name: object) -> str:
    if not isinstance(name, str):
        return ""
    return name.split("}", 1)[1] if name.startswith("{") else name


def _remove(node: etree._Element) -> None:
    parent = node.getparent()
    if parent is None:
        return
    if node.tail:
        previous = node.getprevious()
        if previous is not None:
            previous.tail = (previous.tail or "") + node.tail
        else:
            parent.text = (parent.text or "") + node.tail
    parent.remove(node)
