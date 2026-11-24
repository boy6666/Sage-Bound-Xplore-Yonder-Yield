"""Parse the academic portal schedule grid (``?c=Default&a=Kb``).

The portal renders one HTML table: the header row holds the weekdays with
``colspan`` (Tuesday and Thursday occupy two physical columns), the first column
holds the period and its time range, and each course cell carries
``name / teacher / room / weeks`` separated by ``<br>``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

_VOID = {"br", "img", "input", "meta", "link", "hr"}
_TIME_RE = re.compile(r"(\d{1,2}:\d{2})\s*[-–~]\s*(\d{1,2}:\d{2})")
_PERIOD_RE = re.compile(r"第(\d{1,2})节|午(\d{1,2})节")
_WEEK_RANGE_RE = re.compile(r"(\d{1,2})\s*[-–~]\s*(\d{1,2})\s*周(?:\(([^)]*)\)|（([^）]*)）)?")
_SINGLE_WEEK_RE = re.compile(r"(\d{1,2})\s*周(?:\(([^)]*)\)|（([^）]*)）)?")


class _Node:
    __slots__ = ("tag", "attrs", "children")

    def __init__(self, tag: str, attrs) -> None:
        self.tag = tag
        self.attrs = dict(attrs)
        self.children: list = []


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("#root", [])
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_Node(tag, attrs))

    def handle_endtag(self, tag):
        if tag in _VOID:
            return
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _text(node: _Node) -> str:
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
        elif child.tag == "br":
            parts.append("\n")
        else:
            parts.append(_text(child))
    return "".join(parts)


def _iter(node: _Node):
    for child in node.children:
        if isinstance(child, _Node):
            yield child
            yield from _iter(child)


def _cells(tr: _Node) -> list[_Node]:
    return [c for c in tr.children if isinstance(c, _Node) and c.tag in ("td", "th")]


def _span(node: _Node, name: str) -> int:
    raw = node.attrs.get(name)
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return 1
    return value if value > 0 else 1


@dataclass(frozen=True)
class ScheduleCell:
    course_name: str
    class_label: str | None
    teacher: str | None
    location: str | None
    weekday: int
    period_start: int
    period_end: int
    start_time: str
    end_time: str
    weeks: tuple[int, ...]
    weeks_label: str

    @property
    def external_id(self) -> str:
        suffix = self.class_label or ""
        return f"{self.course_name}|{suffix}" if suffix else self.course_name


@dataclass(frozen=True)
class ParsedSchedule:
    term_label: str | None
    term_value: str | None
    cells: tuple[ScheduleCell, ...]

    def courses(self) -> dict[str, ScheduleCell]:
        seen: dict[str, ScheduleCell] = {}
        for cell in self.cells:
            seen.setdefault(cell.external_id, cell)
        return seen


def _split_brackets(raw: str) -> tuple[str, str | None]:
    """``软件质量与测试(A)(24软件)(1班)`` -> (name, "A 24软件 1班")."""
    match = re.match(r"^(?P<name>[^(（]+)(?P<rest>[（(].*)?$", raw.strip())
    if not match:
        return raw.strip(), None
    name = match.group("name").strip()
    rest = match.group("rest") or ""
    parts = re.findall(r"[（(]([^)）]*)[)）]", rest)
    label = " ".join(part.strip() for part in parts if part.strip()) or None
    return name, label


def _weeks_of(raw: str) -> tuple[list[int], str]:
    weeks: set[int] = set()
    labels: list[str] = []
    for match in _WEEK_RANGE_RE.finditer(raw):
        start, end = int(match.group(1)), int(match.group(2))
        mode = (match.group(3) or match.group(4) or "").strip()
        if start > end:
            start, end = end, start
        span = list(range(start, end + 1))
        if "单" in mode:
            span = [w for w in span if w % 2 == 1]
        elif "双" in mode:
            span = [w for w in span if w % 2 == 0]
        weeks.update(span)
        labels.append(match.group(0).strip())
    if not weeks:
        for match in _SINGLE_WEEK_RE.finditer(raw):
            if _WEEK_RANGE_RE.match(match.group(0)):
                continue
            value = int(match.group(1))
            if 1 <= value <= 30:
                weeks.add(value)
                labels.append(match.group(0).strip())
    return sorted(weeks), "、".join(labels)


def _parse_cell_text(
    raw: str,
) -> tuple[str, str | None, str | None, str | None, tuple[int, ...], str]:
    lines = [line.strip() for line in raw.replace("\r", "").split("\n")]
    lines = [line for line in lines if line and line != "\xa0"]
    if not lines:
        return "", None, None, None, (), ""

    name, class_label = _split_brackets(lines[0])
    teacher = lines[1] if len(lines) > 1 else None
    location = lines[2] if len(lines) > 2 else None
    if location and set(location.replace(" ", "")) <= {"-"}:
        # The portal prints "---- ---- ----" when no room is assigned yet.
        location = None

    week_source = "\n".join(lines[3:]) if len(lines) > 3 else ""
    weeks, weeks_label = _weeks_of(week_source)
    if location and ("周" in location and ("周" not in week_source)):
        weeks, weeks_label = _weeks_of(location)
        location = lines[2] if len(lines) > 2 else None

    return name, class_label, teacher, location, tuple(weeks), weeks_label


def parse_kb_html(html: str) -> ParsedSchedule:
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()

    table = None
    for node in _iter(builder.root):
        if node.tag != "table":
            continue
        classes = str(node.attrs.get("class", ""))
        if "solid" in classes or "data" in classes:
            if any(tr for tr in _iter(node) if tr.tag == "tr"):
                table = node
                break
    if table is None:
        raise ValueError("未找到课程表容器（页面结构可能已变化）")

    rows = [tr for tr in _iter(table) if tr.tag == "tr"]
    if not rows:
        raise ValueError("课程表没有数据行")

    header = [cell for cell in _cells(rows[0]) if cell.tag == "th"]
    weekday_by_col: dict[int, int] = {}
    if header:
        column = 1
        weekday = 1
        for cell in header[1:]:
            span = _span(cell, "colspan")
            for offset in range(span):
                weekday_by_col[column + offset] = weekday
            column += span
            weekday += 1

    grid: dict[tuple[int, int], tuple[_Node, int, int]] = {}
    occupied: set[tuple[int, int]] = set()
    row_index = 0
    period_meta: dict[int, tuple[int, str, str]] = {}

    for tr in rows:
        cells = _cells(tr)
        if not cells or all(cell.tag == "th" for cell in cells):
            continue
        column = 0
        first_cell = True
        for cell in cells:
            while (row_index, column) in occupied:
                column += 1
            rowspan, colspan = _span(cell, "rowspan"), _span(cell, "colspan")
            for dr in range(rowspan):
                for dc in range(colspan):
                    occupied.add((row_index + dr, column + dc))
            grid[(row_index, column)] = (cell, rowspan, colspan)
            if first_cell:
                text = _text(cell)
                period_match = _PERIOD_RE.search(text)
                time_match = _TIME_RE.search(text)
                if period_match and time_match:
                    period = int(period_match.group(1) or period_match.group(2))
                    period_meta[row_index] = (period, time_match.group(1), time_match.group(2))
                first_cell = False
            column += colspan
        row_index += 1

    if not period_meta:
        raise ValueError("未解析到节次时间（页面结构可能已变化）")

    total_rows = row_index
    cells_out: list[ScheduleCell] = []
    for (row, column), (cell, rowspan, _colspan) in sorted(grid.items()):
        if column == 0:
            continue
        weekday = weekday_by_col.get(column)
        if weekday is None:
            continue
        raw = _text(cell)
        if not raw.strip() or raw.strip() in {"\xa0", "&nbsp;"}:
            continue
        name, class_label, teacher, location, weeks, weeks_label = _parse_cell_text(raw)
        if not name:
            continue
        if row not in period_meta:
            continue
        period_start, start_time, _ = period_meta[row]
        end_row = min(row + rowspan - 1, total_rows - 1)
        end_meta = period_meta.get(end_row, period_meta[row])
        cells_out.append(
            ScheduleCell(
                course_name=name,
                class_label=class_label,
                teacher=teacher,
                location=location,
                weekday=weekday,
                period_start=period_start,
                period_end=end_meta[0],
                start_time=start_time,
                end_time=end_meta[2],
                weeks=weeks,
                weeks_label=weeks_label,
            )
        )

    term_label = None
    term_value = None
    for node in _iter(builder.root):
        if node.tag == "select" and node.attrs.get("id") == "tm_id":
            for option in _iter(node):
                if option.tag == "option" and "selected" in option.attrs:
                    term_label = _text(option).strip()
                    term_value = option.attrs.get("value")
                    break
            break

    cells_out.sort(key=lambda c: (c.weekday, c.period_start, c.course_name))
    return ParsedSchedule(term_label=term_label, term_value=term_value, cells=tuple(cells_out))