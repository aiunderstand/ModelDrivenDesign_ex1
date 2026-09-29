"""draw.io documents: reading pages and cells, writing cells and pages.

Diagram-agnostic. draw.io has no UML layer of its own — a diagram is styled
cells — so each diagram type recognises and draws its own shapes on top of this.
"""
import base64
import html
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zlib

# Colours every comparison drawing uses for the four statuses (draw.io's palette).
STATUS = {
    "changed":   ("#ffe6cc", "#d79b00"),   # amber
    "missing":   ("#f8cecc", "#b85450"),   # red
    "extra":     ("#d5e8d4", "#82b366"),   # green
    "uncounted": ("#f5f5f5", "#999999"),   # grey
}


# ------------------------------------------------------------------------ reading

class Page:
    """The first page of a .drawio file: its cells and how they nest.

    Each cell is (id, label, mxCell element). Cells wrapped in a UserObject (as
    draw.io does when a cell has a tooltip or custom properties) are unwrapped,
    and compressed pages are decompressed.
    """

    def __init__(self, path):
        root = ET.parse(path).getroot()
        diagram = root.find("diagram") if root.tag == "mxfile" else None
        model = _model(diagram) if diagram is not None else root

        self.cells = []
        for el in model.iter():
            if el.tag == "mxCell" and el.get("id"):
                self.cells.append((el.get("id"), el.get("value") or "", el))
            elif el.tag in ("UserObject", "object"):
                inner = el.find("mxCell")
                if inner is not None:
                    self.cells.append((el.get("id"), el.get("label") or "", inner))
        self._children = {}
        for cell in self.cells:
            self._children.setdefault(cell[2].get("parent"), []).append(cell)

    def children(self, cid):
        return self._children.get(cid, [])


def _model(diagram):
    model = diagram.find("mxGraphModel")
    if model is not None:
        return model
    data = zlib.decompress(base64.b64decode((diagram.text or "").strip()), -15)
    return ET.fromstring(urllib.parse.unquote(data.decode()))


def geometry(cell):
    """{x, y, width, height} of a cell, as floats; empty if it has no geometry."""
    g = cell.find("mxGeometry")
    return {k: float(g.get(k, 0)) for k in ("x", "y", "width", "height")} if g is not None else {}


def lines(label):
    """A draw.io HTML label -> its lines of plain text."""
    text = re.sub(r"<br\s*/?>|</div>|</p>", "\n", label or "", flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    stripped = (html.unescape(line).replace("\xa0", " ").strip() for line in text.split("\n"))
    return [line for line in stripped if line]


def font(style):
    """fontStyle bits (1 bold, 2 italic, 4 underline). The last occurrence wins, as in draw.io."""
    found = re.findall(r"fontStyle=(\d+)", style or "")
    return int(found[-1]) if found else 0


# ------------------------------------------------------------------------ writing

def attr(html_text):
    """HTML label -> XML attribute value (draw.io escapes labels twice)."""
    return html.escape(html_text, quote=True)


def cell(cid, value, style, parent, geometry_xml, kind="vertex", extra="", tooltip=None):
    """One mxCell; wrapped in a UserObject when it carries a hover tooltip."""
    flags = f'{kind}="1" parent="{parent}"{extra}'
    if tooltip is None:
        return (f'        <mxCell id="{cid}" value="{attr(value)}" style="{style}" {flags}>\n'
                f'{geometry_xml}'
                f'        </mxCell>')
    tip = html.escape(tooltip, quote=True).replace("\n", "&#10;")
    return (f'        <UserObject id="{cid}" label="{attr(value)}" tooltip="{tip}">\n'
            f'        <mxCell style="{style}" {flags}>\n'
            f'{geometry_xml}'
            f'        </mxCell>\n'
            f'        </UserObject>')


def paint(style, status, part):
    """Add a status colour to a style. part: 'shape', 'row' or 'edge'."""
    if status is None:
        return style
    fill, stroke = STATUS[status]
    if part == "shape":
        return style + f"fillColor={fill};swimlaneFillColor={fill};strokeColor={stroke};strokeWidth=2;"
    if part == "row":
        return style + f"fillColor={fill};"
    return style + f"strokeColor={stroke};strokeWidth=3;fontColor={stroke};"


def legend(prefix, title, subtitle, rows, x, y=40, w=300):
    """A key for a comparison page: a titled box with one colour swatch per row.

    rows: [(status or None, text)]; None draws an uncoloured swatch.
    """
    row_h, head_h = 26, 46
    lid = f"{prefix}legend"
    head = (f"<b>{html.escape(title)}</b><br>"
            f"<font style=\"font-size:10px\">{html.escape(subtitle)}</font>")
    cells = [
        f'        <mxCell id="{lid}" value="{attr(head)}" '
        f'style="rounded=1;arcSize=6;whiteSpace=wrap;html=1;align=left;verticalAlign=top;'
        f'spacingLeft=8;spacingTop=4;fillColor=#ffffff;strokeColor=#666666;" '
        f'vertex="1" parent="{prefix}1">\n'
        f'          <mxGeometry x="{x}" y="{y}" width="{w}" '
        f'height="{head_h + row_h * len(rows) + 8}" as="geometry" />\n'
        f'        </mxCell>']
    for n, (status, text) in enumerate(rows):
        fill, stroke = STATUS.get(status, ("#ffffff", "#666666"))
        cells.append(
            f'        <mxCell id="{lid}-{n}" value="{attr(html.escape(text))}" '
            f'style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=6;fontSize=11;'
            f'fillColor={fill};strokeColor={stroke};" vertex="1" parent="{lid}">\n'
            f'          <mxGeometry x="8" y="{head_h + n * row_h}" width="{w - 16}" '
            f'height="{row_h - 4}" as="geometry" />\n'
            f'        </mxCell>')
    return cells


def mxfile(pages):
    """pages: [(name, id, cells)] -> a complete .drawio document."""
    out = ['<mxfile host="app.diagrams.net" agent="umlverify" version="24.7.17">']
    for name, pid, cells in pages:
        out.append(
            f'  <diagram name="{html.escape(name)}" id="{pid}">\n'
            '    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" '
            'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            'pageWidth="1654" pageHeight="1169" math="0" shadow="0">\n'
            '      <root>\n'
            f'        <mxCell id="{pid}-0" />\n'
            f'        <mxCell id="{pid}-1" parent="{pid}-0" />\n'
            + "\n".join(cells) + "\n"
            '      </root>\n'
            '    </mxGraphModel>\n'
            '  </diagram>')
    out.append("</mxfile>\n")
    return "\n".join(out)
