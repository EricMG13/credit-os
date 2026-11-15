"""The owner-set wording of delivery: loader, strict schema, template filler, dates, states, bands.

Every sentence, month name, state word and band lives in ``wording.json``; nothing here
holds a word a reader sees. The entry key names are declared here so a file that drops
or adds an entry is refused.
"""

import datetime
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from importlib import resources
from typing import NamedTuple, NoReturn

from credit_os.delivery.errors import DeliveryRefused

ENTRY_KEYS = frozenset(
    {
        "home.subtitle",
        "home.applied_label",
        "home.count_line",
        "home.count_line_adjusted",
        "card.as_of",
        "card.note_newer_running",
        "card.progress",
        "history.subtitle",
        "history.subtitle_one",
        "history.subtitle_unfinished",
        "history.empty",
        "history.text.finished",
        "history.text.capped",
        "history.text.interrupted",
        "history.text.failed",
        "history.text.rejected",
        "history.text.running",
        "history.text.queued",
        "changes.none.title",
        "changes.none.text",
        "changes.pending.title",
        "changes.pending.text",
        "overview.metrics_label",
        "overview.modules_summary",
        "overview.gaps_link",
    }
)
STATE_WORDS = frozenset(
    {"Queued", "Running", "Finished", "Failed", "Capped", "Rejected", "Interrupted"}
)
_NAME = re.compile(r"[a-z][a-z0-9_]*")
_STORE_NAME = re.compile(r"\*|[a-z][a-z0-9_]{0,63}")
_NUMBER = re.compile(r"-?[0-9]+(\.[0-9]+)?")
_ISO = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})", re.ASCII)
_TOP = frozenset({"schema", "not_recorded", "months", "states", "measures", "templates"})


def _refuse(rule: str, key: str | None = None) -> NoReturn:
    raise DeliveryRefused(f"wording: {rule}" if key is None else f"wording: {rule} ({key})")


class Band(NamedTuple):
    label: str
    min: Decimal | None
    max: Decimal | None


class Measure(NamedTuple):
    name: str
    bands: tuple[Band, ...]


@dataclass(frozen=True)
class _Entry:
    placeholders: frozenset[str]
    count: str | None
    count_min: int
    # variant name ("text", "zero", "one", "other") -> parts: literal text or ("name",)
    variants: Mapping[str, tuple[str | tuple[str], ...]]


def _slot(text: str, start: int, key: str) -> tuple[str, int]:
    """Read the `{name}` opened at `start`; return the name and the index of its `}`."""
    end = start + 1
    while end < len(text) and text[end] not in "{}":
        end += 1
    if end >= len(text) or text[end] == "{":
        _refuse("an unclosed open brace in a template", key)
    name = text[start + 1 : end]
    if not _NAME.fullmatch(name):
        _refuse("a placeholder name outside [a-z][a-z0-9_]*", key)
    return name, end


def _scan(text: str, key: str) -> tuple[str | tuple[str], ...]:
    """One linear pass: `{name}` is a slot; any other brace is a load error."""
    parts: list[str | tuple[str]] = []
    literal: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "}":
            _refuse("a lone close brace in a template", key)
        if ch != "{":
            literal.append(ch)
            i += 1
            continue
        name, end = _slot(text, i, key)
        if literal:
            parts.append("".join(literal))
            literal = []
        parts.append((name,))
        i = end + 1
    if literal:
        parts.append("".join(literal))
    return tuple(parts)


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    out: dict[str, object] = {}
    for k, v in pairs:
        if k in out:
            _refuse("a duplicate JSON key")
        out[k] = v
    return out


def _no_constant(_: str) -> NoReturn:
    _refuse("NaN or Infinity in JSON")


def _no_float(_: str) -> NoReturn:
    _refuse("a float in JSON")


def _obj(value: object, rule: str, key: str | None = None) -> dict[str, object]:
    if not isinstance(value, dict):
        _refuse(rule, key)
    return value


def _str(value: object, rule: str, key: str | None = None) -> str:
    if not isinstance(value, str):
        _refuse(rule, key)
    return value


def _months(value: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
    months = _obj(value, "months must be an object")
    if set(months) != {"short", "long"}:
        _refuse("months must hold exactly short and long")
    out: list[tuple[str, ...]] = []
    for name in ("short", "long"):
        names = months[name]
        if not isinstance(names, list) or len(names) != 12:
            _refuse("months need 12 names", name)
        if not all(isinstance(n, str) and n for n in names):
            _refuse("month names must be non-empty strings", name)
        out.append(tuple(str(n) for n in names))
    return out[0], out[1]


def _end_reason(reason: object, status: str) -> str | None:
    """Null, "*" (any reason) or a store name; an ended status needs a reason."""
    if reason is not None and (not isinstance(reason, str) or not _STORE_NAME.fullmatch(reason)):
        _refuse("a state end_reason must be null, * or a store name", status)
    if (reason is None) != (status in ("created", "running")):
        _refuse("an ended status needs an end reason; created and running none", status)
    return reason


def _states(value: object) -> dict[tuple[str, str | None], str | None]:
    if not isinstance(value, list):
        _refuse("states must be a list")
    table: dict[tuple[str, str | None], str | None] = {}
    for item in value:
        row = _obj(item, "a state must be an object")
        if set(row) != {"status", "end_reason", "word"}:
            _refuse("a state needs status, end_reason and word")
        status = _str(row["status"], "a state status must be a string")
        reason = _end_reason(row["end_reason"], status)
        word = row["word"]
        if word is not None and (not isinstance(word, str) or word not in STATE_WORDS):
            _refuse("a state word is outside the closed set", status)
        if (status, reason) in table:
            _refuse("a state pair appears twice", status)
        table[(status, reason)] = word
    for status, reason in table:
        if reason == "*" and any(s == status and r != "*" for s, r in table):
            _refuse("a star end reason sits beside an exact one", status)
    return table


def _bound(value: object, key: str) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _NUMBER.fullmatch(value):
        _refuse("a band bound must be null or a decimal string", key)
    return Decimal(value)


def _band(raw: object, seen: list[Band], key: str) -> Band:
    band = _obj(raw, "a band must be an object", key)
    if set(band) != {"label", "min", "max"}:
        _refuse("a band needs label, min and max", key)
    label = _str(band["label"], "a band label must be a string", key)
    if any(b.label == label for b in seen):
        _refuse("a band label repeats within its measure", key)
    low = _bound(band["min"], key)
    high = _bound(band["max"], key)
    if low is not None and high is not None and not low < high:
        _refuse("a band min must be below its max", key)
    return Band(label, low, high)


def _measure(key: str, raw: object) -> Measure:
    item = _obj(raw, "a measure must be an object", key)
    if set(item) != {"name", "bands"}:
        _refuse("a measure needs name and bands", key)
    name = _str(item["name"], "a measure name must be a string", key)
    raw_bands = item["bands"]
    if not isinstance(raw_bands, list):
        _refuse("measure bands must be a list", key)
    bands: list[Band] = []
    for raw_band in raw_bands:
        bands.append(_band(raw_band, bands, key))
    return Measure(name, tuple(bands))


def _measures(value: object) -> dict[str, Measure]:
    items = _obj(value, "measures must be an object")
    return {key: _measure(key, raw) for key, raw in items.items()}


def _placeholders(value: object, key: str) -> frozenset[str]:
    if not isinstance(value, list):
        _refuse("placeholders must be a list", key)
    names: list[str] = []
    for name in value:
        if not isinstance(name, str) or not _NAME.fullmatch(name):
            _refuse("a declared placeholder name is outside [a-z][a-z0-9_]*", key)
        if name in names:
            _refuse("a placeholder is declared twice", key)
        names.append(name)
    return frozenset(names)


def _plural(item: dict[str, object], key: str) -> bool:
    """Check which variant fields an entry holds; True when it is plural."""
    allowed = {"placeholders", "text", "zero", "one", "other", "count", "count_min"}
    if "placeholders" not in item or not set(item) <= allowed:
        _refuse("a template entry holds unknown or missing fields", key)
    plural = "one" in item or "other" in item
    if plural and not ("one" in item and "other" in item):
        _refuse("plural variants need one and other", key)
    if "zero" in item and not plural:
        _refuse("zero needs one and other beside it", key)
    if plural == ("text" in item):
        _refuse("an entry has text or plural variants, not both or neither", key)
    return plural


def _count_fields(
    item: dict[str, object], declared: frozenset[str], plural: bool, key: str
) -> tuple[str | None, int]:
    count_min = item.get("count_min", 0)
    if not isinstance(count_min, int) or isinstance(count_min, bool) or count_min < 0:
        _refuse("count_min must be an int of 0 or more", key)
    if ("count" in item) != (plural or "count_min" in item):
        _refuse("count is present exactly with plural variants or count_min", key)
    if "count" not in item:
        return None, count_min
    count = item["count"]
    if not isinstance(count, str) or count not in declared:
        _refuse("count must name a declared placeholder", key)
    return count, count_min


def _variants(
    item: dict[str, object], declared: frozenset[str], key: str
) -> dict[str, tuple[str | tuple[str], ...]]:
    variants: dict[str, tuple[str | tuple[str], ...]] = {}
    for name in ("text", "zero", "one", "other"):
        if name in item:
            parts = _scan(_str(item[name], "a template variant must be a string", key), key)
            used = {p[0] for p in parts if isinstance(p, tuple)}
            # The zero variant may leave the count out ("No filter applied"); every
            # other variant names each declared placeholder at least once.
            if used != declared and not (name == "zero" and used < declared):
                _refuse("a variant's placeholders differ from the declared set", key)
            variants[name] = parts
    return variants


def _entry(key: str, raw: object) -> _Entry:
    item = _obj(raw, "a template entry must be an object", key)
    plural = _plural(item, key)
    declared = _placeholders(item["placeholders"], key)
    count, count_min = _count_fields(item, declared, plural, key)
    return _Entry(declared, count, count_min, _variants(item, declared, key))


def _templates(value: object) -> dict[str, _Entry]:
    items = _obj(value, "templates must be an object")
    if set(items) != ENTRY_KEYS:
        _refuse("templates must hold exactly the declared entries")
    return {key: _entry(key, raw) for key, raw in items.items()}


def _date_parts(iso: str) -> tuple[int, int, str]:
    if not isinstance(iso, str):
        raise TypeError("an ISO date must be a str")
    match = _ISO.fullmatch(iso)
    if match is None:
        _refuse("a date must be YYYY-MM-DD")
    year, month, day = match.groups()
    try:
        datetime.date(int(year), int(month), int(day))
    except ValueError:
        _refuse("a date must be a real calendar date")
    return int(day), int(month), year


def _check_values(spec: _Entry, values: Mapping[str, object], entry: str) -> None:
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            _refuse("a value must be a str or an int", entry)
        if isinstance(value, int) and value < 0:
            _refuse("an int value must not be negative", entry)
        if name == spec.count and (not isinstance(value, int) or value < spec.count_min):
            _refuse("the count must be an int at or above count_min", entry)


def _variant(spec: _Entry, values: Mapping[str, object]) -> str:
    if "text" in spec.variants or spec.count is None:
        return "text"
    n = values[spec.count]
    if n == 0 and "zero" in spec.variants:
        return "zero"
    return "one" if n == 1 else "other"


@dataclass(frozen=True)
class Wording:
    """The loaded wording; build it only with `load_wording`."""

    not_recorded: str
    measures: Mapping[str, Measure]
    _short: tuple[str, ...]
    _long: tuple[str, ...]
    _states: Mapping[tuple[str, str | None], str | None]
    _entries: Mapping[str, _Entry]

    def fill(self, entry: str, values: Mapping[str, object]) -> str:
        spec = self._entries.get(entry)
        if spec is None:
            _refuse("an undeclared template entry", entry)
        if set(values) != spec.placeholders:
            _refuse("values must name exactly the entry's placeholders", entry)
        _check_values(spec, values, entry)
        out: list[str] = []
        for part in spec.variants[_variant(spec, values)]:
            out.append(str(values[part[0]]) if isinstance(part, tuple) else part)
        return "".join(out)

    def state_word(self, status: str, end_reason: str | None) -> str | None:
        if (status, end_reason) in self._states:
            return self._states[(status, end_reason)]
        if isinstance(end_reason, str) and (status, "*") in self._states:
            return self._states[(status, "*")]
        _refuse(f"no wording for run state {status!r} with end reason {end_reason!r}")

    def display_date(self, iso: str) -> str:
        day, month, year = _date_parts(iso)
        return f"{day} {self._short[month - 1]} {year}"

    def month_year(self, iso: str) -> str:
        _, month, year = _date_parts(iso)
        return f"{self._long[month - 1]} {year}"


def load_wording(data: bytes | None = None) -> Wording:
    """Load and validate the wording; None reads the package's own `wording.json`."""
    if data is None:
        data = resources.files("credit_os.delivery").joinpath("wording.json").read_bytes()
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        _refuse("the wording file must be ASCII")
    try:
        top = json.loads(
            text,
            object_pairs_hook=_no_duplicates,
            parse_constant=_no_constant,
            parse_float=_no_float,
        )
    except json.JSONDecodeError:
        _refuse("the wording file is not valid JSON")
    root = _obj(top, "the wording file must be an object")
    if set(root) != _TOP:
        _refuse("the wording file must hold exactly the declared top-level keys")
    schema = root["schema"]
    if isinstance(schema, bool) or schema != 1:
        _refuse("schema must be the int 1")
    short, long = _months(root["months"])
    return Wording(
        not_recorded=_str(root["not_recorded"], "not_recorded must be a string"),
        measures=_measures(root["measures"]),
        _short=short,
        _long=long,
        _states=_states(root["states"]),
        _entries=_templates(root["templates"]),
    )
