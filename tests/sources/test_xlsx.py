"""The xlsx reader's answer key: each row's fixture is built here by hand-written XML and the
expected text is a literal. Rows come from the 1D PR 3 key table and the controller's rulings."""

import io
import tracemalloc
import zipfile
from typing import Literal

import pytest

from credit_os.sources import Page, SourcePages, SourceUnreadable, xlsx
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
D1904 = "Workbook date system: 1904; date serials are retained without conversion."


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
    "<si><t>non\N{NO-BREAK SPACE}breaking</t></si>"  # 9
)
STYLES = (
    '<numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0.00"/></numFmts>'
    '<cellXfs count="4"><xf numFmtId="0"/><xf numFmtId="164"/><xf numFmtId="14"/><xf/></cellXfs>'
)
FORMATTED = (
    '<numFmts><numFmt numFmtId="164" formatCode="{}"/></numFmts>'
    '<cellXfs><xf numFmtId="{}"/></cellXfs>'
)
LONG = "n" * 255
BOOK = "'xl/workbook.xml': "
RELS = "'xl/_rels/workbook.xml.rels': "
ONE = '<row r="1"><c r="A1"><v>1</v></c></row>'
SHEET = "'xl/worksheets/sheet1.xml': "


def cells(
    xml: str,
    *,
    strings: str | None = None,
    styles: str | None = None,
    name: str = "Annual FY",
    sheet_attrs: str = "",
    workbook_extra: str = "",
) -> bytes:
    return book(
        f'<row r="1">{xml}</row>',
        strings=strings,
        styles=styles,
        name=name,
        sheet_attrs=sheet_attrs,
        workbook_extra=workbook_extra,
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
    # no row or cell references: counted from 1
    (
        "a1",
        book('<row><c><v>1</v></c><c><v>2</v></c></row><row><c t="b"><v>1</v></c></row>'),
        one_page("A1=1 | B1=2\nA2=TRUE"),
    ),
    # a cell without a reference follows the one before it
    (
        "a2",
        cells('<c r="C1"><v>1</v></c><c><v>2</v></c><c r="AA1"><v>3</v></c><c><v>4</v></c>'),
        one_page("C1=1 | D1=2 | AA1=3 | AB1=4"),
    ),
    # a row without a number follows the one before it; an empty row writes no line
    (
        "a3",
        book('<row r="5"><c><v>1</v></c></row><row/><row><c><v>2</v></c></row>'),
        one_page("A5=1\nA7=2"),
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
    # (ruling 3a) every row without r, every cell with one
    (
        "nr1",
        book('<row><c r="A1"><v>1</v></c></row><row><c r="B2"><v>2</v></c></row>'),
        one_page("A1=1\nB2=2"),
    ),
    # (ruling 3a) every row with r, every cell without
    (
        "nr2",
        book('<row r="3"><c><v>1</v></c><c><v>2</v></c></row><row r="5"><c><v>3</v></c></row>'),
        one_page("A3=1 | B3=2\nA5=3"),
    ),
    # (design 10.1 a4) an empty reference is no reference
    ("a4", cells('<c r=""><v>1</v></c>'), one_page("A1=1")),
    # (design 10.1 k1) booleans, an error, a date, an unknown kind
    (
        "k1",
        cells(
            '<c r="A1" t="b"><v>0</v></c><c r="B1" t="b"><v>2</v></c>'
            '<c r="C1" t="e"><v>#DIV/0!</v></c>'
            '<c r="D1" t="d"><v>2025-12-31T00:00:00Z</v></c><c r="E1" t="weird"><v>x y</v></c>'
        ),
        one_page("A1=FALSE | B1=2 | C1=#DIV/0! | D1=2025-12-31T00:00:00Z | E1=x y"),
    ),
    # (design 10.1 k2) a number is its stored text, spaces and all
    (
        "k2",
        cells('<c r="A1"><v> 7 </v></c><c r="B1"><v>1E+3</v></c>'),
        one_page("A1= 7  | B1=1E+3"),
    ),
    # (design 10.1 k3) a formula string result is quoted nowhere: str kind without a formula is
    (
        "k3",
        cells('<c r="A1" t="str"><v>Hello</v></c><c r="B1" t="str"><f>A1</f><v>Hello</v></c>'),
        one_page("A1='Hello' | B1='=A1' cache=Hello"),
    ),
    # (design 10.1 k4) a sheet name of exactly 255 characters
    (
        "k4",
        cells('<c r="A1"><v>1</v></c>', name=LONG),
        one_page("A1=1", header=head(LONG)),
    ),
    # (design 10.1 k5) a number format of exactly 255 characters
    (
        "k5",
        cells('<c r="A1"><v>1</v></c>', styles=FORMATTED.format("0" * 255, "164")),
        one_page("A1=1 format='" + "0" * 255 + "'"),
    ),
    # (design 10.1 k6) a built-in number format id of ten digits
    (
        "k6",
        cells('<c r="A1"><v>1</v></c>', styles=FORMATTED.format("0", "9999999999")),
        one_page("A1=1 format='builtin:9999999999'"),
    ),
    # (design 10.1 s1) shared strings: plain, runs, phonetic text left out, own text before runs
    (
        "s1",
        cells(
            '<c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c>'
            '<c r="D1" t="s"><v>3</v></c>',
            strings=STRINGS,
        ),
        one_page("A1='Revenue' | B1='USD millions' | C1='Base' | D1='ownrun'"),
    ),
    # (design 10.1 s2) the text before a child element; references; an astral character
    (
        "s2",
        cells(
            '<c r="A1" t="s"><v>4</v></c><c r="B1" t="s"><v>5</v></c><c r="C1" t="s"><v>8</v></c>',
            strings=STRINGS,
        ),
        one_page("A1='before' | B1='R&D \N{EURO SIGN} \U0001f600' | C1='any tag'"),
    ),
    # (design 10.1 s3) an empty string writes no cell; a blank one does; repr escapes a no-break space
    (
        "s3",
        cells(
            '<c r="A1" t="s"><v>6</v></c><c r="B1" t="s"><v>7</v></c><c r="C1" t="s"><v>9</v></c>',
            strings=STRINGS,
        ),
        one_page("B1='  ' | C1='non\\xa0breaking'"),
    ),
    # (design 10.1 s4) an inline string: own text then runs; a v beside it is not the text
    (
        "s4",
        cells(
            '<c r="A1" t="inlineStr"><v>9</v><is><r><t>b</t></r><t>a</t></is></c>'
            '<c r="B1" t="inlineStr"><is><t>x</t></is><is><t>y</t></is></c>'
        ),
        one_page("A1='ab' | B1='xy'"),
    ),
    # (design 10.1 s5) a quote and a backslash in a string are written as repr writes them
    (
        "s5",
        cells(
            '<c r="A1" t="inlineStr"><is><t>it\'s</t></is></c>'
            '<c r="B1" t="inlineStr"><is><t>a\\b</t></is></c>'
            '<c r="C1" t="inlineStr"><is><t>both \' and "</t></is></c>'
        ),
        one_page("A1=\"it's\" | B1='a\\\\b' | C1='both \\' and \"'"),
    ),
    # (design 10.1 f1) a custom format, a built-in one, General, a format entry without an id
    (
        "f1",
        cells(
            '<c r="A1" s="1"><v>1</v></c><c r="B1" s="2"><v>45000</v></c>'
            '<c r="C1" s="0"><v>3</v></c><c r="D1" s="3"><v>4</v></c>',
            styles=STYLES,
        ),
        one_page("A1=1 format='#,##0.00' | B1=45000 format='builtin:14' | C1=3 | D1=4"),
    ),
    # (design 10.1 f2) a format is shown for the number kind only, and not on a formula
    (
        "f2",
        cells(
            '<c r="A1" s="1" t="b"><v>1</v></c><c r="B1" s="1" t="str"><v>x</v></c>'
            '<c r="C1" s="1"><f>A1</f><v>5</v></c><c r="D1" s="1" t="n"><v>6</v></c>',
            styles=STYLES,
        ),
        one_page("A1=TRUE | B1='x' | C1='=A1' cache=5 | D1=6 format='#,##0.00'"),
    ),
    # (design 10.1 f3) no styles part: no format, and the style index is not checked
    ("f3", cells('<c r="A1" s="99"><v>1</v></c>'), one_page("A1=1")),
    # (design 10.1 f4) a styles part without cell formats: the same
    (
        "f4",
        cells('<c r="A1" s="99"><v>1</v></c>', styles="<fonts><font/></fonts>"),
        one_page("A1=1"),
    ),
    # (design 10.1 f5) number formats after the cell formats still apply; a repeated id takes the last
    (
        "f5",
        cells(
            '<c r="A1" s="0"><v>1</v></c>',
            styles='<cellXfs><xf numFmtId="200"/></cellXfs>'
            '<numFmts><numFmt numFmtId="200" formatCode="0.0"/>'
            '<numFmt numFmtId="200" formatCode="0.000"/></numFmts>',
        ),
        one_page("A1=1 format='0.000'"),
    ),
    # (design 10.1 m1) a formula with a cache; without text; with a quote; a boolean cache
    (
        "m1",
        cells(
            '<c r="A1"><f>SUM(B1:C1)</f><v>10</v></c><c r="B1"><f t="shared" si="0"/><v>4</v></c>'
            '<c r="C1"><f>\'S 1\'!A1</f><v>6</v></c><c r="D1" t="b"><f>TRUE()</f><v>1</v></c>'
        ),
        one_page(
            "A1='=SUM(B1:C1)' cache=10 | "
            "B1='=[shared/array formula; see formula metadata]' cache=4 | "
            "C1='='S 1'!A1' cache=6 | D1='=TRUE()' cache=1"
        ),
    ),
    # (design 10.1 m2) the first f and the first v of a cell; text after a child is not the text
    (
        "m2",
        cells(
            '<c r="A1"><f>A2</f><f>A3</f><v>1</v><v>2</v></c><c r="B1"><v>3<x/>4</v></c>'
            '<c r="C1"><v>5<!-- c -->6</v></c><c r="D1"><v><![CDATA[7]]></v></c>'
        ),
        one_page("A1='=A2' cache=1 | B1=3 | C1=56 | D1=7"),
    ),
    # (design 10.1 w1) the 1904 date system
    (
        "w1",
        cells('<c r="A1"><v>1</v></c>', workbook_extra='<workbookPr date1904="1"/>'),
        one_page("A1=1", header=head(date=D1904)),
    ),
    # (design 10.1 w2) the first workbookPr decides
    (
        "w2",
        cells(
            '<c r="A1"><v>1</v></c>',
            workbook_extra='<workbookPr/><workbookPr date1904="true"/>',
        ),
        one_page("A1=1"),
    ),
    # (design 10.1 w3) a sheet name is written as it is
    (
        "w3",
        cells('<c r="A1"><v>1</v></c>', name="P&amp;L \N{EURO SIGN} 100% it's"),
        one_page("A1=1", header=head("P&L \N{EURO SIGN} 100% it's")),
    ),
    # (design 10.1 n1) blank styled cells, an empty v, cells outside sheetData, a v in an extension
    (
        "n1",
        book(
            '<row r="1"><c r="A1" s="0"/><c r="B1"><v></v></c>'
            '<c r="C1"><extLst><ext><v>9</v></ext></extLst></c><c r="D1"><v>1</v></c></row>',
            after='<row r="9"><c r="A9"><v>8</v></c></row>'
            '<mergeCells><mergeCell ref="A1:B2"/></mergeCells>',
        ),
        one_page("D1=1"),
    ),
    # (design 10.1 n2) a second sheetData is read after the first
    (
        "n2",
        book(
            '<row r="1"><c r="A1"><v>1</v></c></row>',
            after='<sheetData><row r="2"><c r="A2"><v>2</v></c></row></sheetData>',
        ),
        one_page("A1=1\nA2=2"),
    ),
    # (design 10.1 n3) elements in no namespace are not cells; a prefixed namespace is
    (
        "n3",
        zipped(
            {
                "xl/workbook.xml": workbook_xml(
                    '<sheet name="Annual FY" sheetId="1" r:id="rId1"/>'
                ),
                "xl/_rels/workbook.xml.rels": rels_xml(REL),
                "xl/worksheets/sheet1.xml": f'<x:worksheet xmlns:x="{MAIN}"><x:sheetData>'
                '<x:row r="1"><x:c r="A1"><x:v>1</x:v></x:c><c r="B1"><v>2</v></c></x:row>'
                "</x:sheetData></x:worksheet>",
            }
        ),
        one_page("A1=1"),
    ),
    # (design 10.1 x1) a byte-order mark and an XML declaration; a declared encoding is not followed
    (
        "x1",
        zipped(
            {
                "xl/workbook.xml": workbook_xml(
                    '<sheet name="Annual FY" sheetId="1" r:id="rId1"/>'
                ),
                "xl/_rels/workbook.xml.rels": rels_xml(REL),
                "xl/worksheets/sheet1.xml": b"\xef\xbb\xbf"
                + (
                    '<?xml version="1.0" encoding="ISO-8859-1"?>'
                    + sheet_xml(
                        '<row r="1"><c r="A1" t="inlineStr"><is>'
                        "<t>caf\N{LATIN SMALL LETTER E WITH ACUTE} &#8364;&#x1F600;</t>"
                        "</is></c></row>"
                    )
                ).encode(),
            }
        ),
        one_page("A1='caf\N{LATIN SMALL LETTER E WITH ACUTE} \N{EURO SIGN}\U0001f600'"),
    ),
    # (design 10.1 x2) relationship targets: absolute, through .., doubled slash; the last Id wins
    (
        "x2",
        zipped(
            {
                "xl/workbook.xml": workbook_xml(
                    '<sheet name="Annual FY" sheetId="1" r:id="rId1"/>'
                ),
                "xl/_rels/workbook.xml.rels": rels_xml(
                    '<Relationship Id="rId1" Target="worksheets/none.xml"/>'
                    '<Relationship Id="rId1" Target="/xl/../xl/./worksheets//sheet1.xml"/>'
                ),
                "xl/worksheets/sheet1.xml": sheet_xml(ONE),
            }
        ),
        one_page("A1=1"),
    ),
    # (design 10.1 c1) a formula over two lines, and a cached string of two lines
    (
        "c1",
        cells(
            '<c r="A1"><f>IF(B1,\n1,2)</f><v>1</v></c>'
            '<c r="B1" t="str"><f>C1</f><v>a\nb</v></c><c r="C1"><v>3</v></c>'
        ),
        one_page("A1='=IF(B1,\\n1,2)' cache=1 | B1='=C1' cache='a\\nb' | C1=3"),
    ),
    # (design 10.1 c2) a tab in a number, and a line break in a sheet name
    (
        "c2",
        cells('<c r="A1"><v>1\t2</v></c>', name="A&#10;B"),
        one_page("A1='1\\t2'", header=head("'A\\nB'")),
    ),
    # (ruling 33) the last row, stated
    (
        "row-max-stated",
        book('<row r="1048576"><c r="A1048576"><v>1</v></c></row>'),
        one_page("A1048576=1"),
    ),
    # (ruling 33) the last row, counted
    (
        "row-max-counted",
        book('<row r="1048575"><c><v>1</v></c></row><row><c><v>2</v></c></row>'),
        one_page("A1048575=1\nA1048576=2"),
    ),
    # (finding M-1) a hidden range whose max is negative hides nothing; a later cell still reads
    (
        "hidden-negative-max",
        book(
            '<row r="1"><c r="A1"><v>1</v></c><c r="C1"><v>3</v></c></row>',
            before='<cols><col min="1" max="-2" hidden="1"/></cols>',
        ),
        one_page("A1=1 | C1=3"),
    ),
    # (finding M-1) a negative max does not move the flags an earlier range set
    (
        "hidden-negative-max-after-range",
        book(
            '<row r="1"><c r="A1"><v>1</v></c><c r="O1"><v>15</v></c><c r="CV1"><v>100</v></c></row>',
            before=(
                '<cols><col min="100" max="100" hidden="1"/>'
                '<col min="1" max="-16300" hidden="1"/></cols>'
            ),
        ),
        one_page("A1=1 | O1=15 | CV1=100 [hidden column]"),
    ),
    # (finding M-1, survivors hide_columns m20) column 1 hidden
    (
        "hidden-a",
        book(
            '<row r="1"><c r="A1"><v>1</v></c></row>',
            before='<cols><col min="1" max="1" hidden="1"/></cols>',
        ),
        one_page("A1=1 [hidden column]"),
    ),
    # (finding M-1, survivors hide_columns m26, m27) two ranges, the higher first
    (
        "hidden-two-ranges",
        book(
            '<row r="1"><c r="B1"><v>2</v></c><c r="D1"><v>4</v></c><c r="E1"><v>5</v></c></row>',
            before='<cols><col min="5" max="5" hidden="1"/><col min="2" max="2" hidden="1"/></cols>',
        ),
        one_page("B1=2 [hidden column] | D1=4 | E1=5 [hidden column]"),
    ),
    # (finding M-1, survivor hide_columns m37) an inverted range hides nothing
    (
        "hidden-inverted",
        book(
            '<row r="1"><c r="I1"><v>9</v></c></row>',
            before='<cols><col min="9" max="8" hidden="1"/></cols>',
        ),
        one_page("I1=9"),
    ),
]


@pytest.mark.parametrize(("raw", "pages"), [pytest.param(r, p, id=i) for i, r, p in TEXT_ROWS])
def test_text_rows(raw: bytes, pages: tuple[Page, ...]) -> None:
    assert xlsx_pages("b.xlsx", raw) == SourcePages(pages=pages, encoding=None)


ORDER = SHEET + "sheet 'Annual FY': "
DRIVE = zipped(
    {
        "xl/workbook.xml": workbook_xml('<sheet name="Annual FY" sheetId="1" r:id="rId1"/>'),
        "xl/_rels/workbook.xml.rels": rels_xml(
            '<Relationship Id="rId1" Target="C:/xl/worksheets/sheet1.xml"/>'
        ),
        "xl/worksheets/sheet1.xml": sheet_xml(ONE),
    }
)


def dotdot() -> bytes:
    parts: dict[str, str | bytes] = {
        "xl/workbook.xml": workbook_xml('<sheet name="Annual FY" sheetId="1" r:id="rId1"/>'),
        "xl/_rels/workbook.xml.rels": rels_xml(REL),
        "xl/worksheets/../worksheets/sheet1.xml": sheet_xml(ONE),
    }
    return zipped(parts)


REFUSALS = [
    # no cell with text in any sheet
    ("r1", book(""), "has no text"),
    # (ruling 3) a duplicate cell
    (
        "r3",
        cells('<c r="A1"><v>1</v></c><c r="A1"><v>2</v></c>'),
        ORDER + "cell A1 out of order in row 1",
    ),
    # (ruling 3) cells right to left
    (
        "r4",
        cells('<c r="B1"><v>1</v></c><c r="A1"><v>2</v></c>'),
        ORDER + "cell A1 out of order in row 1",
    ),
    # (ruling 3) rows out of order
    (
        "r5",
        book('<row r="2"><c r="A2"><v>1</v></c></row><row r="1"><c r="A1"><v>2</v></c></row>'),
        ORDER + "row 1 after row 2",
    ),
    # (ruling 3) a row number twice
    ("r6", book('<row r="2"/><row r="2"/>'), ORDER + "row 2 after row 2"),
    # (ruling 3) row zero
    ("r7", book('<row r="0"/>'), ORDER + "row 0 after row 0"),
    # a drive-letter target is resolved under xl/ and looked up by exact name
    ("dl1", DRIVE, "'xl/C:/xl/worksheets/sheet1.xml': the part is missing"),
    # a member stored under a name holding .. is never read by a normalised target
    ("dd1", dotdot(), "'xl/worksheets/sheet1.xml': the part is missing"),
    # (design 10.2 r2) only a blank string
    ("r2", cells('<c r="A1" t="inlineStr"><is><t> </t></is></c>'), "has no text"),
    # (design 10.2 r8) a row number with a leading zero
    ("r8", book('<row r="01"/>'), SHEET + "a row number that is not a whole number"),
    # (design 10.2 r9) a row number that is text
    ("r9", book('<row r="x"/>'), SHEET + "a row number that is not a whole number"),
    # (design 10.2 r10) a reference to another row
    (
        "r10",
        book('<row r="2"><c r="A7"><v>1</v></c></row>'),
        SHEET + "a cell reference that is not a cell of row 2",
    ),
    # (design 10.2 r11) a reference in lower case
    (
        "r11",
        cells('<c r="a1"><v>1</v></c>'),
        SHEET + "a cell reference that is not a cell of row 1",
    ),
    # (design 10.2 r12) a reference with a leading zero
    (
        "r12",
        cells('<c r="A01"><v>1</v></c>'),
        SHEET + "a cell reference that is not a cell of row 1",
    ),
    # (design 10.2 r13) a reference past column XFD
    (
        "r13",
        cells('<c r="XFE1"><v>1</v></c>'),
        SHEET + "a cell beyond column XFD in row 1",
    ),
    # (design 10.2 r14) a counted cell past column XFD
    (
        "r14",
        cells('<c r="XFD1"><v>1</v></c><c><v>2</v></c>'),
        SHEET + "a cell beyond column XFD in row 1",
    ),
    # (design 10.2 r15) a shared-string index past the end
    (
        "r15",
        cells('<c r="A1" t="s"><v>10</v></c>', strings=STRINGS),
        SHEET + "cell A1: a shared-string index out of range",
    ),
    # (design 10.2 r16) a shared-string cell without a value
    (
        "r16",
        cells('<c r="A1" t="s"/>', strings=STRINGS),
        SHEET + "cell A1: a shared-string index out of range",
    ),
    # (design 10.2 r17) a shared-string cell and no shared strings
    (
        "r17",
        cells('<c r="A1" t="s"><v>0</v></c>'),
        SHEET + "cell A1: a shared-string index out of range",
    ),
    # (design 10.2 r18) a shared-string index that is text
    (
        "r18",
        cells('<c r="A1" t="s"><v>x</v></c>', strings=STRINGS),
        SHEET + "cell A1: a shared-string index that is not a whole number",
    ),
    # (design 10.2 r19) a style index past the end
    (
        "r19",
        cells('<c r="B1" s="4"><v>1</v></c>', styles=STYLES),
        SHEET + "cell B1: a style index out of range",
    ),
    # (design 10.2 r20) a negative style index, without styles
    (
        "r20",
        cells('<c r="A1" s="-1"><v>1</v></c>'),
        SHEET + "cell A1: a style index out of range",
    ),
    # (design 10.2 r21) a style index that is text, on a blank cell
    (
        "r21",
        cells('<c r="A1" s="x"/>'),
        SHEET + "cell A1: a style index that is not a whole number",
    ),
    # (design 10.2 r22) column settings after the cells
    (
        "r22",
        book(ONE, after='<cols><col min="1" max="1" hidden="1"/></cols>'),
        SHEET + "column settings after the cells",
    ),
    # (design 10.2 r23) a hidden column range without max
    (
        "r23",
        book(ONE, before='<cols><col min="1" hidden="1"/></cols>'),
        SHEET + "a hidden column range without whole numbers",
    ),
    # (design 10.2 r24) a number format without a code
    (
        "r24",
        cells('<c r="A1"><v>1</v></c>', styles='<numFmts><numFmt numFmtId="5"/></numFmts>'),
        "'xl/styles.xml': a number format without an id or a code",
    ),
    # (design 10.2 r25) a sheet without a name
    (
        "r25",
        zipped(
            {
                "xl/workbook.xml": workbook_xml('<sheet sheetId="1" r:id="rId1"/>'),
                "xl/_rels/workbook.xml.rels": rels_xml(REL),
            }
        ),
        BOOK + "a sheet without a name",
    ),
    # (design 10.2 r26) a sheet without a relationship id
    (
        "r26",
        zipped(
            {
                "xl/workbook.xml": workbook_xml('<sheet name="A" id="rId1"/>'),
                "xl/_rels/workbook.xml.rels": rels_xml(REL),
            }
        ),
        BOOK + "a sheet without a relationship id",
    ),
    # (design 10.2 r27) no sheets
    (
        "r27",
        zipped(
            {
                "xl/workbook.xml": workbook_xml(""),
                "xl/_rels/workbook.xml.rels": rels_xml(REL),
            }
        ),
        BOOK + "has no sheets",
    ),
    # (design 10.2 r28) two sheets of one name
    (
        "r28",
        sheets(("Same", "", ONE), ("Same", "", ONE)),
        BOOK + "two sheets named 'Same'",
    ),
    # (design 10.2 r29) a relationship that is not there
    (
        "r29",
        zipped(
            {
                "xl/workbook.xml": workbook_xml('<sheet name="A" r:id="rId9"/>'),
                "xl/_rels/workbook.xml.rels": rels_xml(REL),
            }
        ),
        BOOK + "sheet 'A' names a relationship that is missing",
    ),
    # (design 10.2 r30) a relationship without an Id
    (
        "r30",
        zipped(
            {
                "xl/workbook.xml": workbook_xml('<sheet name="A" r:id="rId1"/>'),
                "xl/_rels/workbook.xml.rels": rels_xml('<Relationship Target="x"/>'),
            }
        ),
        RELS + "a relationship without an Id",
    ),
    # (design 10.2 r31) an external relationship
    (
        "r31",
        sheets(
            ("A", "", ONE),
            rels='<Relationship Id="rId1" Target="https://example.invalid/sheet1.xml" '
            'TargetMode="External"/>',
        ),
        RELS + "sheet 'A' is an external relationship",
    ),
    # (design 10.2 r32) a relationship without a Target
    (
        "r32",
        sheets(("A", "", ONE), rels='<Relationship Id="rId1"/>'),
        RELS + "sheet 'A' has a relationship without a Target",
    ),
    # (design 10.2 r33) a target that leaves xl/
    (
        "r33",
        sheets(("A", "", ONE), rels='<Relationship Id="rId1" Target="../docProps/app.xml"/>'),
        RELS + "sheet 'A' has a relationship that leaves the workbook",
    ),
    # (design 10.2 r34) an absolute target outside xl/
    (
        "r34",
        sheets(("A", "", ONE), rels='<Relationship Id="rId1" Target="/etc/passwd"/>'),
        RELS + "sheet 'A' has a relationship that leaves the workbook",
    ),
    # (design 10.2 r35) a target that climbs out and back by another name
    (
        "r35",
        sheets(
            ("A", "", ONE),
            rels='<Relationship Id="rId1" Target="../../xl/worksheets/sheet1.xml"/>',
        ),
        RELS + "sheet 'A' has a relationship that leaves the workbook",
    ),
    # (design 10.2 r36) a target with a backslash
    (
        "r36",
        sheets(
            ("A", "", ONE),
            rels='<Relationship Id="rId1" Target="worksheets\\sheet1.xml"/>',
        ),
        RELS + "sheet 'A' has a relationship target with a backslash",
    ),
    # (design 10.2 r37) a target that names no part
    (
        "r37",
        sheets(("A", "", ONE), rels='<Relationship Id="rId1" Target="worksheets/none.xml"/>'),
        "'xl/worksheets/none.xml': the part is missing",
    ),
    # (design 10.2 r38) no relationships part
    (
        "r38",
        zipped({"xl/workbook.xml": workbook_xml('<sheet name="A" r:id="rId1"/>')}),
        RELS + "the part is missing",
    ),
    # (design 10.2 r39) a Strict Open XML workbook
    (
        "r39",
        zipped(
            {"xl/workbook.xml": '<workbook xmlns="http://purl.oclc.org/ooxml/spreadsheetml/main"/>'}
        ),
        BOOK + "a Strict Open XML workbook, which is not read",
    ),
    # (design 10.2 r40) a workbook part with another root
    (
        "r40",
        zipped({"xl/workbook.xml": f'<worksheet xmlns="{MAIN}"/>'}),
        BOOK + "the root element is not a workbook",
    ),
    # (design 10.2 r41) a sheet name of 256 characters
    (
        "r41",
        cells('<c r="A1"><v>1</v></c>', name=LONG + "n"),
        BOOK + "a sheet name longer than 255 characters",
    ),
    # (design 10.2 r42) a relationship id of 256 characters
    (
        "r42",
        zipped(
            {
                "xl/workbook.xml": workbook_xml(f'<sheet name="A" r:id="{LONG}n"/>'),
                "xl/_rels/workbook.xml.rels": rels_xml(REL),
            }
        ),
        BOOK + "a relationship id longer than 255 characters",
    ),
    # (design 10.2 r43) a relationship target of 256 characters
    (
        "r43",
        sheets(("A", "", ONE), rels=f'<Relationship Id="rId1" Target="{LONG}n"/>'),
        RELS + "a relationship target longer than 255 characters",
    ),
    # (design 10.2 r44) a number format of 256 characters
    (
        "r44",
        cells('<c r="A1"><v>1</v></c>', styles=FORMATTED.format("0" * 256, "164")),
        "'xl/styles.xml': a number format longer than 255 characters",
    ),
    # (design 10.2 r45) a number format id that is text
    (
        "r45",
        cells('<c r="A1"><v>1</v></c>', styles=FORMATTED.format("0", "general")),
        "'xl/styles.xml': a number format id that is not a number",
    ),
    # (design 10.2 r46) a number format id of eleven digits
    (
        "r46",
        cells('<c r="A1"><v>1</v></c>', styles=FORMATTED.format("0", "10000000000")),
        "'xl/styles.xml': a number format id that is not a number",
    ),
    # (design 10.2 r47) a defined number format id that is negative
    (
        "r47",
        cells(
            '<c r="A1"><v>1</v></c>',
            styles='<numFmts><numFmt numFmtId="-1" formatCode="0"/></numFmts>',
        ),
        "'xl/styles.xml': a number format id that is not a number",
    ),
    # (ruling 33) a stated row above the last
    (
        "row-over-stated",
        book('<row r="1048577"><c><v>1</v></c></row>'),
        SHEET + "a row beyond row 1,048,576",
    ),
    # (ruling 33) a counted row above the last
    (
        "row-over-counted",
        book('<row r="1048576"><c><v>1</v></c></row><row><c><v>2</v></c></row>'),
        SHEET + "a row beyond row 1,048,576",
    ),
]


@pytest.mark.parametrize(("raw", "message"), [pytest.param(r, m, id=i) for i, r, m in REFUSALS])
def test_refusal_rows(raw: bytes, message: str) -> None:
    with pytest.raises(SourceUnreadable) as caught:
        xlsx_pages("b.xlsx", raw)
    assert str(caught.value) == "b.xlsx: " + message


def test_page_text_cap_applies_within_a_row(monkeypatch: pytest.MonkeyPatch) -> None:
    # (finding H1) the cap is checked as each label is written, so one row cannot pass it
    monkeypatch.setattr(xlsx, "MAX_TEXT_CHARACTERS", 65_536)
    raw = book(
        '<row><c t="s"><v>0</v></c><c t="s"><v>0</v></c></row>',
        strings="<si><t>" + "x" * 40_000 + "</t></si>",
    )
    with pytest.raises(SourceUnreadable) as caught:
        xlsx_pages("b.xlsx", raw)
    assert str(caught.value) == "b.xlsx: page text longer than 65,536 characters"


def test_page_text_cap_is_met_before_a_later_style_fault(monkeypatch: pytest.MonkeyPatch) -> None:
    # (finding M-2) on the pre-fix reader this row is refused for the style index instead
    # ("cell C1: a style index out of range"), so it fails for H1's cause
    monkeypatch.setattr(xlsx, "MAX_TEXT_CHARACTERS", 65_536)
    raw = book(
        '<row><c t="s"><v>0</v></c><c t="s"><v>0</v></c><c s="5"><v>1</v></c></row>',
        strings="<si><t>" + "x" * 40_000 + "</t></si>",
        styles='<cellXfs count="1"><xf/></cellXfs>',
    )
    with pytest.raises(SourceUnreadable) as caught:
        xlsx_pages("b.xlsx", raw)
    assert str(caught.value) == "b.xlsx: page text longer than 65,536 characters"


CAP_REFUSED = SHEET + "a cell or string longer than 1,048,576 characters"
ASTRAL = chr(0xE0001)  # repr writes it as ten characters


def label_book(text: str) -> bytes:
    # inline-string cell A1: its label is "A1=" + repr(text); deflated so the zip is far under 1 MiB
    return book(
        f'<row><c r="A1" t="inlineStr"><is><t>{text}</t></is></c></row>',
        method=zipfile.ZIP_DEFLATED,
    )


def label_cap_shape() -> bytes:
    # the 9 KiB reviewer shape (x-shared-formula-hidden), one U+E0001 trimmed from the formula and
    # from the shared string so each part expands to under 8 MiB: its label is about 21 Mi characters
    n = 1_048_576
    return book(
        '<row hidden="1"><c t="s"><f>' + ASTRAL * (n - 3) + "\n</f><v>0</v></c></row>",
        before='<cols><col min="1" max="1" hidden="1"/></cols>',
        strings="<si><t>" + ASTRAL * (n - 2) + "\n</t></si>",
        method=zipfile.ZIP_DEFLATED,
    )


def test_label_cap_shape() -> None:
    # (ruling 37) the shared-string cache and the repr count against the cell cap
    with pytest.raises(SourceUnreadable) as caught:
        xlsx_pages("b.xlsx", label_cap_shape())
    assert str(caught.value) == "b.xlsx: " + CAP_REFUSED


def test_label_cap_early() -> None:
    # (ruling 37) the refusal comes before the next piece of the label is built
    raw = label_cap_shape()
    with pytest.raises(SourceUnreadable):
        xlsx_pages("b.xlsx", raw)
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        with pytest.raises(SourceUnreadable):
            xlsx_pages("b.xlsx", raw)
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert peak < 24 * 1024 * 1024


def test_label_at_cap() -> None:
    # (ruling 37) a label of exactly 1,048,576 characters reads
    pages = xlsx_pages("b.xlsx", label_book("a" * 1_048_571))
    assert pages.pages[0].text == H + "A1='" + "a" * 1_048_571 + "'"


def test_label_over_cap() -> None:
    # (ruling 37) one more character is refused
    with pytest.raises(SourceUnreadable) as caught:
        xlsx_pages("b.xlsx", label_book("a" * 1_048_572))
    assert str(caught.value) == "b.xlsx: " + CAP_REFUSED


def test_label_at_cap_repr() -> None:
    # (ruling 37) counted after repr: 104,857 x 10 + 1 + 5 = 1,048,576
    pages = xlsx_pages("b.xlsx", label_book(ASTRAL * 104_857 + "a"))
    assert pages.pages[0].text == H + "A1='" + "\\U000e0001" * 104_857 + "a'"


def test_label_over_cap_repr() -> None:
    # (ruling 37) one more character after repr is refused
    with pytest.raises(SourceUnreadable) as caught:
        xlsx_pages("b.xlsx", label_book(ASTRAL * 104_857 + "aa"))
    assert str(caught.value) == "b.xlsx: " + CAP_REFUSED


def formula_book(formula: str) -> bytes:
    return book(f'<row><c r="A1"><f>{formula}</f></c></row>', method=zipfile.ZIP_DEFLATED)


@pytest.mark.parametrize(
    ("formula", "written"),
    [
        pytest.param(ASTRAL * 200_000, ASTRAL * 200_000, id="formula-langtag-long"),
        pytest.param("\\" * 524_288, "\\" * 524_288, id="formula-backslash-long"),
    ],
)
def test_formula_floor_is_the_written_length(formula: str, written: str) -> None:
    # (ruling 37) a formula written unescaped counts its raw length, not its repr's
    pages = xlsx_pages("b.xlsx", formula_book(formula))
    assert pages.pages[0].text == H + "A1='=" + written + "' cache=[absent]"


def pieces_book(n: int) -> bytes:
    # n one-character pieces: a processing instruction flushes the parser's text buffer after each
    text = (chr(0x100) + "<?a?>") * n
    return book(
        f'<row><c r="A1" t="inlineStr"><is><t>{text}</t></is></c></row>',
        method=zipfile.ZIP_DEFLATED,
    )


def test_pieces_memory() -> None:
    # (ruling 38) a text of 1,048,571 one-character pieces reads in under 24 MiB
    raw = pieces_book(1_048_576 - 5)
    assert len(raw) < 1_048_576
    xlsx_pages("b.xlsx", raw)
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        pages = xlsx_pages("b.xlsx", raw)
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert len(pages.pages) == 1
    assert pages.pages[0].text == H + "A1='" + chr(0x100) * (1_048_576 - 5) + "'"
    assert peak < 24 * 1024 * 1024


def test_cache_floor_memory() -> None:
    # (ruling 39) a formula near the cap and a long shared-string cache is refused at the cache
    # before the formula label is built, so the peak stays under 16 MiB
    smile = chr(0x1F600)
    cap = 1_048_576
    raw = book(
        '<row><c t="s"><f>' + smile * (cap - 21) + "</f><v>0</v></c></row>",
        strings="<si><t>" + smile * (cap - 250) + "</t></si>",
        method=zipfile.ZIP_DEFLATED,
    )
    assert len(raw) < 1_048_576
    with pytest.raises(SourceUnreadable):
        xlsx_pages("b.xlsx", raw)
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        with pytest.raises(SourceUnreadable) as caught:
            xlsx_pages("b.xlsx", raw)
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert str(caught.value) == "b.xlsx: " + CAP_REFUSED
    assert peak < 16 * 1024 * 1024


def astral_cache_book(extra: int) -> tuple[bytes, str]:
    # (ruling 39) the byte floor: a shared-string cache of astral characters is counted at
    # 4 bytes a character, so a cache at the cap reads and one character more is refused
    smile = chr(0x1F600)
    cap = 1_048_576
    k = 600_000 + extra
    m = cap - 13 - 600_000
    raw = book(
        '<row r="1"><c r="A1" t="s"><f>' + "x" * m + "</f><v>0</v></c></row>",
        strings="<si><t>" + smile * k + "</t></si>",
        method=zipfile.ZIP_DEFLATED,
    )
    assert len(raw) < 1_048_576
    return raw, "A1=" + "'=" + "x" * m + "'" + " cache=" + smile * k


def test_astral_cache_at_cap() -> None:
    raw, label = astral_cache_book(0)
    assert len(label) == 1_048_576
    pages = xlsx_pages("b.xlsx", raw)
    assert pages.pages[0].text.endswith("\n" + label)
    assert pages.pages[0].state == "text"


def test_astral_cache_over_cap() -> None:
    raw, _ = astral_cache_book(1)
    with pytest.raises(SourceUnreadable) as caught:
        xlsx_pages("b.xlsx", raw)
    assert str(caught.value) == (
        "b.xlsx: 'xl/worksheets/sheet1.xml': a cell or string longer than 1,048,576 characters"
    )
