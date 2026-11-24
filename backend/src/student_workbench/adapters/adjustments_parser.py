"""Parse the portal's 调停补课信息 page (``?c=Default&a=tbk``).

The page holds two tables:

- ``data_table``  : 调停课 (a scheduled class is moved or cancelled)
- ``data_table2`` : 补课   (a class is made up on another date)

Both render "当前没有记录" as a single spanning cell when empty, which is a
definite empty list, not a parse failure.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .html_tree import body_rows, cells, find_table, iter_nodes, parse_html, text
from .kb_parser import split_course_class

_WEEKDAY = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "天": 7}
_EMPTY_HINT = "没有记录"

KIND_CANCEL = "cancel"
KIND_MOVE = "move"
KIND_MAKEUP = "makeup"


@dataclass(frozen=True)
class AdjustmentRecord:
    kind: str
    course_class: str
    course_name: str
    class_label: str | None
    teacher: str | None
    week: int | None
    weekday: int | None
    period_label: str | None
    period_start: int | None
    period_end: int | None
    date: str | None
    room: str | None

    @property
    def external_id(self) -> str:
        raw = "|".join(
            [
                self.kind,
                self.course_class,
                str(self.week),
                str(self.weekday),
                self.period_label or "",
                self.date or "",
                self.room or "",
            ]
        )
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ParsedAdjustments:
    term_label: str | None
    records: tuple[AdjustmentRecord, ...]


def _pick(columns: dict[str, int], *keywords: str, exclude: tuple[str, ...] = ()) -> int | None:
    for label, index in columns.items():
        if any(bad in label for bad in exclude):
            continue
        if any(keyword in label for keyword in keywords):
            return index
    return None


def _cell_text(row, column: int | None) -> str:
    if column is None:
        return ""
    found = cells(row)
    if column >= len(found):
        return ""
    return text(found[column]).replace("\xa0", " ").strip()


def _parse_weekday(raw: str) -> int | None:
    for char, value in _WEEKDAY.items():
        if char in raw:
            return value
    match = re.search(r"[1-7]", raw)
    return int(match.group()) if match else None


def _parse_week(raw: str) -> int | None:
    match = re.search(r"\d{1,2}", raw)
    return int(match.group()) if match else None


def _period_index(token: str) -> int | None:
    """``午2`` -> 102, ``第3``/``3`` -> 3, so 午间节次 never collides with 上午."""
    token = token.strip()
    noon = re.fullmatch(r"午\s*(\d{1,2})", token)
    if noon:
        return 100 + int(noon.group(1))
    plain = re.fullmatch(r"(?:第)?\s*(\d{1,2})", token)
    if plain:
        return int(plain.group(1))
    return None


def _parse_period(raw: str) -> tuple[str | None, int | None, int | None]:
    text = raw.strip()
    if not text:
        return None, None, None
    parts = [part for part in re.split(r"[-–~至]", text) if part.strip()]
    if len(parts) >= 2:
        return text, _period_index(parts[0]), _period_index(parts[1])
    single = _period_index(parts[0])
    return text, single, single


def _kind_of(raw: str, default: str) -> str:
    if "停" in raw:
        return KIND_CANCEL
    if "补" in raw:
        return KIND_MAKEUP
    if "调" in raw:
        return KIND_MOVE
    return default


def _parse_table(table, default_kind: str) -> list[AdjustmentRecord]:
    columns: dict[str, int] = {}
    for row in iter_nodes(table):
        if row.tag != "tr":
            continue
        header_cells = [cell for cell in cells(row) if cell.tag == "th"]
        if header_cells:
            column = 0
            for cell in header_cells:
                label = text(cell).strip()
                if label:
                    columns[label] = column
                column += 1
            break

    if not columns:
        raise ValueError("调停补课表格缺少表头（页面结构可能已变化）")

    kind_col = _pick(columns, "类型")
    class_col = _pick(columns, "课程班", "课程")
    teacher_col = _pick(columns, "教师")
    week_col = _pick(columns, "周", exclude=("星期",))
    weekday_col = _pick(columns, "星期")
    period_col = _pick(columns, "节次", "节")
    date_col = _pick(columns, "日期")
    room_col = _pick(columns, "教室", "地点")

    records: list[AdjustmentRecord] = []
    for row in body_rows(table):
        row_cells = cells(row)
        plain = text(row).strip()
        spanning = bool(row_cells) and int(row_cells[0].attrs.get("colspan", 1) or 1) > 1
        if len(row_cells) == 1 or spanning:
            if _EMPTY_HINT in plain:
                continue
        if not plain or _EMPTY_HINT in plain:
            continue

        course_class = _cell_text(row, class_col)
        if not course_class:
            continue
        course_name, class_label = split_course_class(course_class)
        period_label, period_start, period_end = _parse_period(
            _cell_text(row, period_col)
        )
        records.append(
            AdjustmentRecord(
                kind=_kind_of(_cell_text(row, kind_col), default_kind),
                course_class=course_class,
                course_name=course_name,
                class_label=class_label,
                teacher=_cell_text(row, teacher_col) or None,
                week=_parse_week(_cell_text(row, week_col)),
                weekday=_parse_weekday(_cell_text(row, weekday_col)),
                period_label=period_label,
                period_start=period_start,
                period_end=period_end,
                date=_cell_text(row, date_col) or None,
                room=_cell_text(row, room_col) or None,
            )
        )
    return records


def _term_from_page(root) -> str | None:
    for node in iter_nodes(root):
        if node.tag != "h3":
            continue
        heading = text(node).strip()
        if "调停补课" in heading and "-" in heading:
            return heading.split("-", 1)[1].strip() or None
    return None


def parse_adjustments_html(html: str) -> ParsedAdjustments:
    root = parse_html(html)
    cancel_table = find_table(root, "data_table")
    makeup_table = find_table(root, "data_table2")
    if cancel_table is None and makeup_table is None:
        raise ValueError("未找到调停补课表格（页面结构可能已变化）")

    records: list[AdjustmentRecord] = []
    if cancel_table is not None:
        records.extend(_parse_table(cancel_table, KIND_CANCEL))
    if makeup_table is not None:
        records.extend(_parse_table(makeup_table, KIND_MAKEUP))

    records.sort(key=lambda r: (r.date or "", r.weekday or 0, r.period_start or 0))
    return ParsedAdjustments(term_label=_term_from_page(root), records=tuple(records))