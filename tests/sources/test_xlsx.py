"""The xlsx reader's answer key: each row's fixture is built here by hand-written XML and the
expected text is a literal. Rows come from the 1D PR 3 key table and the controller's rulings."""

import io
import zipfile
from typing import Literal

import pytest

from credit_os.sources import Page, SourcePages, SourceUnreadable
from credit_os.sources.xlsx import xlsx_pages

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def zipped(parts: dict[str, str | bytes], method: int = zipfile.ZIP_STORED) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", method) as archive:
        for name, text in parts.items():
            archive.writestr(name, text)
    return buffer.getvalue()


def workbook_xml(sheets: str, extra: str = "") -> str:
    return (
        f'<workbook xmlns="{MAIN}" xmlns:r="{OFFICE}">{extra}<sheets>{sheets}</sheets></workbook>'
    )


def rels_xml(items: str) -> str:
    return f'<Relationships xmlns="{PKG_REL}">{items}</Relationships>'


def sheet_xml(rows: str, before: str = "", after: str = "") -> str:
    return f'<worksheet xmlns="{MAIN}">{before}<sheetData>{rows}</sheetData>{after}</worksheet>'


def book(
    rows: str,
    *,
    before: str = "",
    after: str = "",
    strings: str | None = None,
    styles: str | None = None,
    name: str = "Annual FY",
    sheet_attrs: str = "",
    workbook_extra: str = "",
    method: int = zipfile.ZIP_STORED,
) -> bytes:
    """One sheet named `name`."""
    parts: dict[str, str | bytes] = {
        "xl/workbook.xml": workbook_xml(
            f'<sheet name="{name}" sheetId="1" r:id="rId1"{sheet_attrs}/>', workbook_extra
        ),
        "xl/_rels/workbook.xml.rels": rels_xml(
            f'<Relationship Id="rId1" Type="{OFFICE}/worksheet" Target="worksheets/sheet1.xml"/>'
        ),
        "xl/worksheets/sheet1.xml": sheet_xml(rows, before, after),
    }
    if strings is not None:
        parts["xl/sharedStrings.xml"] = f'<sst xmlns="{MAIN}">{strings}</sst>'
    if styles is not None:
        parts["xl/styles.xml"] = f'<styleSheet xmlns="{MAIN}">{styles}</styleSheet>'
    return zipped(parts, method)


NOTE = (
    "Workbook values are raw stored lexemes, not Excel display values. Formula caches "
    "may be absent or stale; no recalculation. Charts, drawings and embedded objects "
    "require separate visual review."
)
D1900 = "Workbook date system: 1900; date serials are retained without conversion."


def head(name: str = "Annual FY", date: str = D1900) -> str:
    return f"Sheet {name}\n{NOTE}\n{date}\n"


H = head()
REL = f'<Relationship Id="rId1" Type="{OFFICE}/worksheet" Target="worksheets/sheet1.xml"/>'
STRINGS = (
    "<si><t>Revenue</t></si>"  # 0
    "<si><r><rPr><b/></rPr><t>USD </t></r><r><t>millions</t></r></si>"  # 1
    "<si><t>Base</t><rPh><t>phonetic</t></rPh></si>"  # 2
    "<si><r><t>run</t></r><t>own</t></si>"  # 3: the item's own t first, then the runs
    "<si><t>before<x>in</x>after</t></si>"  # 4: the text before the first child
    "<si><t>R&amp;D \N{EURO SIGN} \U0001f600</t></si>"  # 5
    "<si><t></t></si>"  # 6: empty
    '<si><t xml:space="preserve">  </t></si>'  # 7: two spaces
    "<other><t>any tag</t></other>"  # 8: an item is any child of the root
    "<si><t>non breaking</t></si>"  # 9
)
ONE = '<row r="1"><c r="A1"><v>1</v></c></row>'
SHEET = "'xl/worksheets/sheet1.xml': "


def cells(
    xml: str,
    *,
    strings: str | None = None,
    styles: str | None = None,
    name: str = "Annual FY",
    sheet_attrs: str = "",
) -> bytes:
    return book(
        f'<row r="1">{xml}</row>',
        strings=strings,
        styles=styles,
        name=name,
        sheet_attrs=sheet_attrs,
    )


def sheets(*items: tuple[str, str, str], rels: str | None = None) -> bytes:
    """(name, sheet attributes, rows) per sheet, parts sheet1.xml, sheet2.xml, ..."""
    entries = "".join(
        f'<sheet name="{n}" sheetId="{i}" r:id="rId{i}"{a}/>'
        for i, (n, a, _) in enumerate(items, 1)
    )
    relations = rels or "".join(
        f'<Relationship Id="rId{i}" Type="{OFFICE}/worksheet" Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, len(items) + 1)
    )
    parts: dict[str, str | bytes] = {
        "xl/workbook.xml": workbook_xml(entries),
        "xl/_rels/workbook.xml.rels": rels_xml(relations),
    }
    for i, (_, _, rows) in enumerate(items, 1):
        parts[f"xl/worksheets/sheet{i}.xml"] = sheet_xml(rows)
    return zipped(parts)


def one_page(
    lines: str, state: Literal["text", "empty", "unreadable"] = "text", header: str = H
) -> tuple[Page, ...]:
    return (Page(number=1, text=header + lines, state=state),)


# (id, rule, raw, expected pages)
TEXT_ROWS = [
    # exact lexeme; a formula without a cache
    (
        "t1",
        cells('<c r="A1"><v>9007199254740993.25</v></c><c r="B1"><f>A1*2</f></c>'),
        one_page("A1=9007199254740993.25 | B1='=A1*2' cache=[absent]"),
    ),
    # two stored cells of a sheet whose dimension claims all of it
    (
        "t2",
        book(
            '<row r="1"><c r="A1"><v>1</v></c></row>'
            '<row r="1048576"><c r="XFD1048576"><v>2</v></c></row>',
            before='<dimension ref="A1:XFD1048576"/>',
        ),
        one_page("A1=1\nXFD1048576=2"),
    ),
    # an inline string
    (
        "t3",
        cells('<c r="A1" t="inlineStr"><is><t>USD m</t></is></c>'),
        one_page("A1='USD m'"),
    ),
    # zero, a gap, a formula, a shared string
    (
        "t4",
        cells(
            '<c r="A1"><v>0</v></c><c r="C1"><f>A1+1</f><v></v></c><c r="D1" t="s"><v>0</v></c>',
            strings="<si><t>USD millions</t></si>",
        ),
        one_page("A1=0 | C1='=A1+1' cache=[absent] | D1='USD millions'"),
    ),
    # a hidden row and hidden columns (min to max, 1 and true)
    (
        "h1",
        book(
            '<row r="1"><c r="A1"><v>1</v></c><c r="B1"><v>2</v></c><c r="D1"><v>4</v></c></row>'
            '<row r="2" hidden="1"><c r="A2"><v>5</v></c><c r="C2"><v>6</v></c></row>'
            '<row r="3" hidden="0"><c r="E3"><v>7</v></c></row>',
            before='<cols><col min="2" max="3" hidden="1"/><col min="4" max="4" hidden="0"/>'
            '<col min="5" max="5" hidden="true"/><col min="9" max="8" hidden="1"/></cols>',
        ),
        one_page(
            "A1=1 | B1=2 [hidden column] | D1=4\n"
            "[hidden row] A2=5 | C2=6 [hidden column]\n"
            "E3=7 [hidden column]"
        ),
    ),
    # a hidden sheet
    (
        "h2",
        cells('<c r="A1"><v>1</v></c>', sheet_attrs=' state="veryHidden"'),
        one_page("[hidden sheet]\nA1=1"),
    ),
    # three sheets in workbook order: text, empty, blank text only
    (
        "p1",
        sheets(
            ("First", "", ONE),
            ("Second", "", ""),
            ("Third", "", '<row r="1"><c r="A1" t="inlineStr"><is><t> </t></is></c></row>'),
        ),
        (
            Page(number=1, text=head("First") + "A1=1", state="text"),
            Page(number=2, text=head("Second"), state="empty"),
            Page(number=3, text=head("Third") + "A1=' '", state="empty"),
        ),
    ),
    # two sheets that name one part
    (
        "p2",
        sheets(
            ("One", "", ONE),
            ("Two", "", ""),
            rels='<Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Target="worksheets/sheet1.xml"/>',
        ),
        (
            Page(number=1, text=head("One") + "A1=1", state="text"),
            Page(number=2, text=head("Two") + "A1=1", state="text"),
        ),
    ),
    # a hidden sheet beside a visible one
    (
        "p3",
        sheets(("Shown", ' state="visible"', ONE), ("Workings", ' state="hidden"', ONE)),
        (
            Page(number=1, text=head("Shown") + "A1=1", state="text"),
            Page(number=2, text=head("Workings") + "[hidden sheet]\nA1=1", state="text"),
        ),
    ),
    # a comments part is not read, whatever it holds
    (
        "p4",
        zipped(
            {
                "xl/workbook.xml": workbook_xml(
                    '<sheet name="Annual FY" sheetId="1" r:id="rId1"/>'
                ),
                "xl/_rels/workbook.xml.rels": rels_xml(REL),
                "xl/worksheets/sheet1.xml": sheet_xml(ONE),
                "xl/comments1.xml": '<!DOCTYPE x><comments xmlns="' + MAIN + '"/>',
                "[Content_Types].xml": "<Types/>",
                "docProps/app.xml": "not xml at all",
            }
        ),
        one_page("A1=1"),
    ),
    # (ruling 6, regenerated) a formula on a shared-string cell: the cache is the string
    (
        "m3",
        cells('<c r="A1" t="s"><f>B1</f><v>0</v></c>', strings=STRINGS),
        one_page("A1='=B1' cache=Revenue"),
    ),
]


@pytest.mark.parametrize(("raw", "pages"), [pytest.param(r, p, id=i) for i, r, p in TEXT_ROWS])
def test_text_rows(raw: bytes, pages: tuple[Page, ...]) -> None:
    assert xlsx_pages("b.xlsx", raw) == SourcePages(pages=pages, encoding=None)


REFUSALS = [
    # no cell with text in any sheet
    ("r1", book(""), "has no text"),
]


@pytest.mark.parametrize(("raw", "message"), [pytest.param(r, m, id=i) for i, r, m in REFUSALS])
def test_refusal_rows(raw: bytes, message: str) -> None:
    with pytest.raises(SourceUnreadable) as caught:
        xlsx_pages("b.xlsx", raw)
    assert str(caught.value) == "b.xlsx: " + message
