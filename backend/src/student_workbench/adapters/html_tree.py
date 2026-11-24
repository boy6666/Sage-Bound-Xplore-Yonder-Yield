"""Minimal HTML tree helpers shared by the portal parsers.

Only the pieces the portal pages need: build a tree, read text with ``<br>`` as a
line break, walk nodes, and read table cells with their spans.
"""

from __future__ import annotations

from html.parser import HTMLParser

_VOID = {"br", "img", "input", "meta", "link", "hr"}


class Node:
    __slots__ = ("tag", "attrs", "children")

    def __init__(self, tag: str, attrs) -> None:
        self.tag = tag
        self.attrs = dict(attrs)
        self.children: list = []


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", [])
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        if tag in _VOID:
            return
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_html(html: str) -> Node:
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    return builder.root


def text(node: Node) -> str:
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
        elif child.tag == "br":
            parts.append("\n")
        else:
            parts.append(text(child))
    return "".join(parts)


def iter_nodes(node: Node):
    for child in node.children:
        if isinstance(child, Node):
            yield child
            yield from iter_nodes(child)


def cells(tr: Node) -> list[Node]:
    return [c for c in tr.children if isinstance(c, Node) and c.tag in ("td", "th")]


def span(node: Node, name: str) -> int:
    raw = node.attrs.get(name)
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return 1
    return value if value > 0 else 1


def find_table(root: Node, table_id: str) -> Node | None:
    for node in iter_nodes(root):
        if node.tag == "table" and node.attrs.get("id") == table_id:
            return node
    return None


def header_columns(table: Node) -> dict[str, int]:
    """Map header text to column index using the first ``th`` row."""
    for row in iter_nodes(table):
        if row.tag != "tr":
            continue
        headers = [cell for cell in cells(row) if cell.tag == "th"]
        if not headers:
            continue
        mapping: dict[str, int] = {}
        column = 0
        for cell in headers:
            label = text(cell).strip()
            if label:
                mapping[label] = column
            column += span(cell, "colspan")
        return mapping
    return {}


def body_rows(table: Node) -> list[Node]:
    rows = []
    for row in iter_nodes(table):
        if row.tag != "tr":
            continue
        row_cells = cells(row)
        if row_cells and row_cells[0].tag == "td":
            rows.append(row)
    return rows