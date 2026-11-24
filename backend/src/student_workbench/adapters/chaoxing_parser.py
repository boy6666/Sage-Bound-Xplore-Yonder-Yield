"""Parse the 超星/学习通 "我的作业" aggregate page.

The page renders one ``<li>`` per assignment. The detail URL lives in a ``data``
attribute and carries ``workId``/``courseId``/``classId`` plus a short-lived
``enc`` token. Only the information that the list itself provides is parsed;
deadlines are not part of this page.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

from .html_tree import Node, iter_nodes, parse_html, text

DONE_STATUSES = {"已完成", "已通过", "已批阅", "待批阅"}


@dataclass(frozen=True)
class ParsedWork:
    work_id: str
    title: str
    status: str
    course_id: str | None
    class_id: str | None
    course_name: str | None
    task_url: str

    @property
    def done(self) -> bool:
        return self.status in DONE_STATUSES


def _task_url(node: Node) -> str | None:
    value = node.attrs.get("data")
    if not value or "work/task" not in value:
        return None
    return value


def _course_name(body: str) -> str | None:
    if "《" not in body or "》" not in body:
        return None
    start = body.index("《") + 1
    end = body.index("》", start)
    name = body[start:end].strip()
    return name or None


def parse_all_task(html: str) -> list[ParsedWork]:
    root = parse_html(html)
    works: list[ParsedWork] = []
    for node in iter_nodes(root):
        if node.tag != "li":
            continue
        url = _task_url(node)
        if url is None:
            continue
        query = parse_qs(urlsplit(url).query)
        work_id = (query.get("workId") or [""])[0].strip()
        if not work_id:
            continue

        title = ""
        status = ""
        for child in iter_nodes(node):
            classes = child.attrs.get("class", "")
            if child.tag == "p" and "overHidden2" in classes and not title:
                title = text(child).strip()
            elif child.tag == "span" and "stuStatus" in classes and not status:
                status = text(child).strip()

        body = text(node)
        works.append(
            ParsedWork(
                work_id=work_id,
                title=title or "未命名作业",
                status=status,
                course_id=(query.get("courseId") or [None])[0],
                class_id=(query.get("classId") or [None])[0],
                course_name=_course_name(body),
                task_url=url,
            )
        )
    return works