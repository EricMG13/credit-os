"""The xlsx reader: one page per sheet, each cell the raw lexeme the file stores.

`xlsx_pages` reads through `ooxml.Package` and nothing else of the zip or XML. Each part is read
once, piece by piece, by a table of element paths; of a sheet only its text, a flag per column and
the current row and cell are kept. A workbook is read whole or refused. Comments, drawings and
every other part are not read. Strict Open XML is refused by name. Rows and cells must rise (what
openpyxl 3.1.5 and xlsxwriter 3.3.1 write, checked; not checked against ECMA-376 or Excel), which
makes a duplicate address detectable with no memory.

The bound, as formula arithmetic and not a measurement: peak traced memory of `1.2 x E + 2 x B + a
fixed term measured in PR 3e`, E being the expanded bytes (at most 200 MiB) and B the bytes of the
page text (at most 4 bytes x `MAX_TEXT_CHARACTERS`). At the cap of 32 Mi characters the formula
gives 400 MiB for ASCII or Latin-1 pages, 464 MiB within the BMP and 592 MiB for astral pages.

`Package` uses `warnings.catch_warnings()`, which changes process-wide warning filters, so
`xlsx_pages` is not safe to call from two threads at once. Derivable part names (ECMA-376 Part 2,
6.2.2.3) are not refused by any layer; each name still maps to one member.
"""

import posixpath
import re
from array import array
from collections.abc import Callable
from typing import Literal

from credit_os.sources.errors import SourceUnreadable, shown_name
from credit_os.sources.ooxml import Package
from credit_os.sources.pages import Page, SourcePages

# Limits, read at call time. Sheets: the list and a header per page. Cell and number formats: the
# `xf` list and the format table. Kept characters: a sheet name, relationship id or target and a
# format code stay for the whole read. Cell characters: one cell or string while it is put together.
# Column: XFD, which makes the order of cells checkable. Row: 1,048,576. Text: all pages. Block: pieces of page text
# held before they are made one block.
MAX_SHEETS = 10_000
MAX_CELL_FORMATS = 65_536
MAX_NUMBER_FORMATS = 4_096
MAX_KEPT_CHARACTERS = 255
MAX_ID_DIGITS = 10
MAX_CELL_CHARACTERS = 1_048_576
MAX_COLUMN = 16_384
MAX_ROW = 1_048_576
MAX_TEXT_CHARACTERS = 33_554_432
BLOCK_CHARACTERS = 65_536

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_STRICT_ROOT = "http://purl.oclc.org/ooxml/spreadsheetml/main}workbook"
_PACKAGE = "http://schemas.openxmlformats.org/package/2006/relationships}"
_RELATIONSHIP_ID = "http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
_WORKBOOK = "xl/workbook.xml"
_RELATIONSHIPS = "xl/_rels/workbook.xml.rels"
_STRINGS = "xl/sharedStrings.xml"
_STYLES = "xl/styles.xml"
_NOTE = (
    "Workbook values are raw stored lexemes, not Excel display values. Formula caches may be "
    "absent or stale; no recalculation. Charts, drawings and embedded objects require separate "
    "visual review."
)
_NO_FORMULA = "[shared/array formula; see formula metadata]"
_ABSENT = "[absent]"
_YES = ("1", "true")
_CONTROL = re.compile("[\x00-\x1f\x7f-\x9f\N{LINE SEPARATOR}\N{PARAGRAPH SEPARATOR}]")
_REFERENCE = re.compile("([A-Z]{1,3})([0-9]+)")

Path = tuple[str, ...]


def _plain(text: str) -> str:
    """Return unquoted text as it is, or its `repr` when it would break a page line."""
    return repr(text) if _CONTROL.search(text) else text


def _formula(formula: str) -> str:
    full = "=" + formula
    return repr(full) if _CONTROL.search(full) else f"'{full}'"


def _whole(text: str) -> bool:
    """Return whether text is a whole number in canonical form."""
    try:
        return str(int(text)) == text
    except ValueError:
        return False


def _letters(column: int) -> str:
    letters = ""
    while column:
        column, rest = divmod(column - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


class _Reader:
    """Between `Package.parse` and a part: the path of names in one namespace, and the text of the
    element that is open before its first child."""

    def __init__(self, package: Package, part: str, space: str) -> None:
        self.package = package
        self.part = part
        self.space = space
        self.where: Path = ()
        self.collect: list[str] | None = None
        self.size = 0
        self.on_start: dict[Path, Callable[[dict[str, str]], None]] = {}
        self.on_end: dict[Path, Callable[[], None]] = {}

    def refuse(self, reason: str) -> SourceUnreadable:
        return self.package.refuse(reason, self.part)

    def kept(self, text: str, what: str) -> None:
        if len(text) > MAX_KEPT_CHARACTERS:
            raise self.refuse(f"{what} longer than {MAX_KEPT_CHARACTERS} characters")

    def local(self, name: str) -> str:
        """Return the local name in this reader's namespace; "" for any other, which matches no path."""
        return name[len(self.space) :] if name.startswith(self.space) else ""

    def start(self, name: str, attributes: dict[str, str]) -> None:
        self.collect = None
        self.where += (self.local(name),)
        handler = self.on_start.get(self.where)
        if handler is not None:
            handler(attributes)

    def end(self, name: str) -> None:
        handler = self.on_end.get(self.where)
        if handler is not None:
            handler()
        self.where = self.where[:-1]
        self.collect = None

    def text(self, data: str) -> None:
        if self.collect is not None:
            self.size += len(data)
            if self.size > MAX_CELL_CHARACTERS:
                raise self.refuse(
                    f"a cell or string longer than {MAX_CELL_CHARACTERS:,} characters"
                )
            self.collect.append(data)


class _Workbook(_Reader):
    def __init__(self, package: Package) -> None:
        super().__init__(package, _WORKBOOK, _MAIN)
        self.date1904 = False
        self.sheets: list[tuple[str, str, bool]] = []
        self.names: set[str] = set()
        self.seen = False
        self.on_start = {
            ("workbook", "workbookPr"): self.properties,
            ("workbook", "sheets", "sheet"): self.sheet,
        }

    def start(self, name: str, attributes: dict[str, str]) -> None:
        if not self.where:
            if name == _STRICT_ROOT:
                raise self.refuse("a Strict Open XML workbook, which is not read")
            if name != _MAIN + "workbook":
                raise self.refuse("the root element is not a workbook")
        super().start(name, attributes)

    def properties(self, attributes: dict[str, str]) -> None:
        if not self.seen:
            self.seen = True
            self.date1904 = attributes.get("date1904") in _YES

    def sheet(self, attributes: dict[str, str]) -> None:
        if len(self.sheets) >= MAX_SHEETS:
            raise self.refuse(f"more than {MAX_SHEETS:,} sheets")
        name = attributes.get("name")
        if name is None:
            raise self.refuse("a sheet without a name")
        identifier = attributes.get(_RELATIONSHIP_ID)
        if identifier is None:
            raise self.refuse("a sheet without a relationship id")
        self.kept(name, "a sheet name")
        self.kept(identifier, "a relationship id")
        if name in self.names:
            raise self.refuse(f"two sheets named {shown_name(name)!r}")
        self.names.add(name)
        self.sheets.append((name, identifier, attributes.get("state", "visible") != "visible"))


class _Relationships(_Reader):
    def __init__(self, package: Package, wanted: set[str]) -> None:
        super().__init__(package, _RELATIONSHIPS, _PACKAGE)
        self.wanted = wanted
        self.found: dict[str, tuple[str | None, bool]] = {}
        self.on_start = {("Relationships", "Relationship"): self.relationship}

    def relationship(self, attributes: dict[str, str]) -> None:
        identifier = attributes.get("Id")
        if identifier is None:
            raise self.refuse("a relationship without an Id")
        if identifier in self.wanted:
            target = attributes.get("Target")
            if target is not None:
                self.kept(target, "a relationship target")
            self.found[identifier] = (target, attributes.get("TargetMode") == "External")


class _Strings(_Reader):
    """The shared strings: their UTF-8 bytes in one buffer and each one's end offset."""

    def __init__(self, package: Package) -> None:
        super().__init__(package, _STRINGS, _MAIN)
        self.data = bytearray()
        self.stops = array("I")
        self.own: list[str] = []
        self.runs: list[str] = []
        self.on_start = {
            ("", ""): self.item,
            ("", "", "t"): lambda _attributes: self.gather(self.own),
            ("", "", "r", "t"): lambda _attributes: self.gather(self.runs),
        }
        self.on_end = {("", ""): self.finish}

    def local(self, name: str) -> str:
        """The root and its children are any elements: an item is any child of the root."""
        return "" if len(self.where) < 2 else super().local(name)

    def gather(self, into: list[str]) -> None:
        self.collect = into

    def item(self, _attributes: dict[str, str]) -> None:
        self.own.clear()
        self.runs.clear()
        self.size = 0

    def finish(self) -> None:
        self.data += "".join(self.own + self.runs).encode()
        self.stops.append(len(self.data))

    def string(self, index: int) -> str:
        return self.data[self.stops[index - 1] if index else 0 : self.stops[index]].decode()


class _Styles(_Reader):
    def __init__(self, package: Package) -> None:
        super().__init__(package, _STYLES, _MAIN)
        self.codes: dict[str, str] = {}
        self.formats: list[str] = []
        self.on_start = {
            ("styleSheet", "numFmts", "numFmt"): self.number_format,
            ("styleSheet", "cellXfs", "xf"): self.cell_format,
        }

    def number(self, text: str) -> str:
        if not (text.isascii() and text.isdigit() and len(text) <= MAX_ID_DIGITS):
            raise self.refuse("a number format id that is not a number")
        return text

    def number_format(self, attributes: dict[str, str]) -> None:
        number = attributes.get("numFmtId")
        code = attributes.get("formatCode")
        if number is None or code is None:
            raise self.refuse("a number format without an id or a code")
        self.number(number)
        self.kept(code, "a number format")
        if number not in self.codes and len(self.codes) >= MAX_NUMBER_FORMATS:
            raise self.refuse(f"more than {MAX_NUMBER_FORMATS:,} number formats")
        self.codes[number] = code

    def cell_format(self, attributes: dict[str, str]) -> None:
        if len(self.formats) >= MAX_CELL_FORMATS:
            raise self.refuse(f"more than {MAX_CELL_FORMATS:,} cell formats")
        self.formats.append(self.number(attributes.get("numFmtId", "0")))


class _Text:
    """The text of all pages: blocks of at least `BLOCK_CHARACTERS`, joined once per page."""

    def __init__(self, package: Package) -> None:
        self.package = package
        self.total = 0
        self.held = 0
        self.blocks: list[str] = []
        self.small: list[str] = []

    def add(self, *pieces: str) -> None:
        size = sum(map(len, pieces))
        self.total += size
        if self.total > MAX_TEXT_CHARACTERS:
            raise self.package.refuse(f"page text longer than {MAX_TEXT_CHARACTERS:,} characters")
        self.small.extend(pieces)
        self.held += size
        if self.held >= BLOCK_CHARACTERS:
            self.blocks.append("".join(self.small))
            self.small = []
            self.held = 0

    def finish(self) -> str:
        text = "".join([*self.blocks, *self.small])
        self.blocks = []
        self.small = []
        self.held = 0
        return text


class _Sheet(_Reader):
    def __init__(
        self, package: Package, part: str, name: str, strings: _Strings, styles: _Styles, out: _Text
    ) -> None:
        super().__init__(package, part, _MAIN)
        self.label = f"sheet {shown_name(name)!r}: "
        self.strings = strings
        self.styles = styles
        self.out = out
        self.state: Literal["text", "empty"] = "empty"
        self.hidden = bytearray(MAX_COLUMN + 1)
        self.in_data = False
        self.row = self.column = 0
        self.row_hidden = self.wrote = self.started = False
        self.parts: dict[str, list[str]] = {}
        row = ("worksheet", "sheetData", "row")
        cell = (*row, "c")
        self.on_start = {
            ("worksheet", "cols"): self.columns,
            ("worksheet", "cols", "col"): self.hide_columns,
            ("worksheet", "sheetData"): lambda _attributes: setattr(self, "in_data", True),
            row: self.start_row,
            cell: self.start_cell,
            (*cell, "v"): lambda _attributes: self.take("v", once=True),
            (*cell, "f"): lambda _attributes: self.take("f", once=True),
            (*cell, "is", "t"): lambda _attributes: self.take("t", once=False),
            (*cell, "is", "r", "t"): lambda _attributes: self.take("r", once=False),
        }
        self.on_end = {cell: self.end_cell}

    def columns(self, _attributes: dict[str, str]) -> None:
        if self.in_data:
            raise self.refuse("column settings after the cells")

    def hide_columns(self, attributes: dict[str, str]) -> None:
        if attributes.get("hidden") not in _YES:
            return
        try:
            low, high = int(attributes["min"]), int(attributes["max"])
        except (KeyError, ValueError) as error:
            raise self.refuse("a hidden column range without whole numbers") from error
        low, high = max(low, 1), min(high, MAX_COLUMN)
        if low <= high:
            self.hidden[low : high + 1] = b"\x01" * (high - low + 1)

    def order(self, reason: str) -> SourceUnreadable:
        return self.refuse(self.label + reason)

    def start_row(self, attributes: dict[str, str]) -> None:
        number = self.row + 1
        stated = attributes.get("r")
        if stated:
            long = len(stated) > len(str(MAX_ROW)) and stated.isascii() and stated.isdigit()
            if long and stated[0] != "0":
                raise self.beyond()
            if not _whole(stated):
                raise self.refuse("a row number that is not a whole number")
            number = int(stated)
            if number <= self.row:
                raise self.order(f"row {number} after row {self.row}")
        if number > MAX_ROW:
            raise self.beyond()
        self.row = number
        self.column = 0
        self.row_hidden = attributes.get("hidden") in _YES
        self.started = False

    def beyond(self) -> SourceUnreadable:
        return self.refuse(f"a row beyond row {MAX_ROW:,}")

    def write(self, label: tuple[str, ...], mark: str) -> None:
        """Write one cell's label, given as pieces: the row's line break and mark before its first,
        ` | ` before the rest, and `mark` after it. The label is at most `MAX_CELL_CHARACTERS`."""
        if sum(map(len, label)) > MAX_CELL_CHARACTERS:
            raise self.refuse(f"a cell or string longer than {MAX_CELL_CHARACTERS:,} characters")
        if self.started:
            head = " | "
        else:
            head = ("\n" if self.wrote else "") + ("[hidden row] " if self.row_hidden else "")
            self.started = self.wrote = True
        self.out.add(head, *label, mark)

    def start_cell(self, attributes: dict[str, str]) -> None:
        self.size = 0
        self.parts = {}
        self.kind = attributes.get("t", "n")
        self.style = attributes.get("s", "0")
        self.address = self.locate(attributes.get("r"))

    def locate(self, stated: str | None) -> str:
        """Return the cell's address and move to its column; refuse a misplaced one."""
        column = self.column + 1
        if stated:
            match = _REFERENCE.fullmatch(stated)
            if match is None or match[2] != str(self.row):
                raise self.refuse(f"a cell reference that is not a cell of row {self.row}")
            column = 0
            for letter in match[1]:
                column = column * 26 + ord(letter) - 64
            if column <= self.column:
                raise self.order(f"cell {stated} out of order in row {self.row}")
        if column > MAX_COLUMN:
            raise self.refuse(f"a cell beyond column XFD in row {self.row}")
        self.column = column
        return stated or _letters(column) + str(self.row)

    def take(self, key: str, *, once: bool) -> None:
        """Collect the text of the element that opened; only its first one when `once`."""
        if not once or key not in self.parts:
            self.collect = self.parts.setdefault(key, [])

    def index(self, text: str, what: str) -> int:
        try:
            return int(text)
        except ValueError as error:
            raise self.refuse(
                f"cell {self.address}: a {what} index that is not a whole number"
            ) from error

    def end_cell(self) -> None:
        value = "".join(self.parts.get("v", ""))
        if self.kind == "s":
            index = self.index(value or "-1", "shared-string")
            if not 0 <= index < len(self.strings.stops):
                raise self.refuse(f"cell {self.address}: a shared-string index out of range")
            text = self.strings.string(index)
        elif self.kind == "inlineStr":
            text = "".join(self.parts.get("t", []) + self.parts.get("r", []))
        else:
            text = value
        style = self.index(self.style, "style")
        if style < 0 or (self.styles.formats and style >= len(self.styles.formats)):
            raise self.refuse(f"cell {self.address}: a style index out of range")
        if "f" in self.parts or text.strip():
            self.state = "text"
        label = self.describe(text, value, style)
        if label is not None:
            self.write(label, " [hidden column]" if self.hidden[self.column] else "")

    def describe(self, text: str, value: str, style: int) -> tuple[str, ...] | None:
        """Return the cell's label as pieces, or None when it writes nothing."""
        address = self.address
        if "f" in self.parts:
            formula = "".join(self.parts["f"]) or _NO_FORMULA
            cache = text if self.kind == "s" else value
            return address, "=", _formula(formula), " cache=", _plain(cache) if cache else _ABSENT
        if not text:
            return None
        if self.kind in ("s", "inlineStr", "str"):
            return address, "=", repr(text)
        if self.kind == "b":
            return address, "=", {"1": "TRUE", "0": "FALSE"}.get(text, _plain(text))
        label: tuple[str, ...] = (address, "=", _plain(text))
        if self.kind == "n" and self.styles.formats:
            number = self.styles.formats[style]
            code = self.styles.codes.get(number, "builtin:" + number)
            if code != "builtin:0":
                label += (" format=", repr(code))
        return label


def _target(package: Package, name: str, found: tuple[str | None, bool] | None) -> str:
    """Return the part a sheet's relationship names, refusing one that is not safe to open."""
    shown = f"sheet {shown_name(name)!r} "
    if found is None:
        raise package.refuse(shown + "names a relationship that is missing", _WORKBOOK)
    target, external = found
    if external:
        raise package.refuse(shown + "is an external relationship", _RELATIONSHIPS)
    if target is None:
        raise package.refuse(shown + "has a relationship without a Target", _RELATIONSHIPS)
    if "\\" in target:
        raise package.refuse(shown + "has a relationship target with a backslash", _RELATIONSHIPS)
    part = posixpath.normpath(target[1:] if target.startswith("/") else "xl/" + target)
    if not part.startswith("xl/"):
        raise package.refuse(shown + "has a relationship that leaves the workbook", _RELATIONSHIPS)
    return part


def xlsx_pages(name: str, raw: bytes) -> SourcePages:
    """Return one page per sheet of the workbook, in workbook order, or refuse it."""
    package = Package(name, raw)
    if not package.has(_WORKBOOK):
        raise package.refuse(f"not a workbook: no part {_WORKBOOK}")
    book = _Workbook(package)
    package.parse(_WORKBOOK, book)
    if not book.sheets:
        raise package.refuse("has no sheets", _WORKBOOK)
    relationships = _Relationships(package, {identifier for _, identifier, _ in book.sheets})
    package.parse(_RELATIONSHIPS, relationships)
    strings = _Strings(package)
    if package.has(_STRINGS):
        package.parse(_STRINGS, strings)
    styles = _Styles(package)
    if package.has(_STYLES):
        package.parse(_STYLES, styles)
    out = _Text(package)
    date = f"Workbook date system: {1904 if book.date1904 else 1900}; date serials are retained without conversion."
    pages = []
    for number, (sheet, identifier, hidden) in enumerate(book.sheets, 1):
        part = _target(package, sheet, relationships.found.get(identifier))
        marker = "[hidden sheet]\n" if hidden else ""
        out.add(f"Sheet {_plain(sheet)}\n{_NOTE}\n{date}\n{marker}")
        reader = _Sheet(package, part, sheet, strings, styles, out)
        package.parse(part, reader)
        pages.append(Page(number=number, text=out.finish(), state=reader.state))
    if all(page.state == "empty" for page in pages):
        raise package.refuse("has no text")
    return SourcePages(pages=tuple(pages), encoding=None)
