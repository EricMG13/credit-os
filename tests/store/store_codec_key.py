"""Answer key for the store's money, time and text codecs (2A plan, keys 2 and 3).

Written by the controller from invented values before the code existed. Dates were checked
with the system `date` command, not with the code under test. Implementers do not edit this
file or weaken a comparison against it.
"""

from datetime import UTC, date, datetime, timedelta, timezone, tzinfo
from decimal import Decimal
from types import MappingProxyType

MONEY_TEXT_MAXIMUM = 64  # characters; a longer amount is refused on write and corrupt on read
DETAIL_INT_MINIMUM = -(2**63)
DETAIL_INT_MAXIMUM = 2**63 - 1


class OddZone(tzinfo):
    """A time zone that reports whatever offset it was given, valid or not."""

    def __init__(self, offset: timedelta | None) -> None:
        self._offset = offset

    def utcoffset(self, dt: datetime | None, /) -> timedelta | None:
        return self._offset

    def dst(self, dt: datetime | None, /) -> timedelta | None:
        return None

    def tzname(self, dt: datetime | None, /) -> str | None:
        return "odd"


# --- Money ---------------------------------------------------------------------------------

# Decimal written -> the text stored.
MONEY_WRITTEN: tuple[tuple[Decimal, str], ...] = (
    (Decimal(0), "0"),
    (Decimal("0.00"), "0.00"),
    (Decimal(20), "20"),
    (Decimal("0.00000000001"), "0.00000000001"),
    (Decimal("1E-11"), "0.00000000001"),
    (Decimal("1E+3"), "1000"),
    (Decimal("2.50E+2"), "250"),
    (
        Decimal(1234567890123456789012345678901234567890),
        "1234567890123456789012345678901234567890",
    ),
    (
        Decimal("12345678901234567890.12345678901234567890"),
        "12345678901234567890.12345678901234567890",
    ),
    (Decimal("1E+63"), "1" + "0" * 63),  # 64 characters, the most allowed
    (Decimal("1E-62"), "0." + "0" * 61 + "1"),  # 64 characters
)

# Refused on write (StoreRefused). None is not here: it is written as NULL.
MONEY_WRITE_REFUSED: tuple[object, ...] = (
    Decimal("-0"),
    Decimal("-0.00"),
    Decimal(-1),
    Decimal("NaN"),
    Decimal("sNaN"),
    Decimal("Infinity"),
    Decimal("-Infinity"),
    1.5,
    0.0,
    20,
    0,
    True,
    False,
    "20",
    "0",
    b"20",
    Decimal("1E+64"),  # 65 characters
    Decimal("1E-63"),  # 65 characters
    Decimal("1E+1000000"),  # must be refused without building the text
    Decimal("0E+1000000"),  # refused by its exponent, zero or not
    Decimal("1" * 65),
)

# Text stored -> str() of the Decimal read (the exponent is kept: "0.00" is not "0").
MONEY_READ: tuple[tuple[str, str], ...] = (
    ("0", "0"),
    ("0.00", "0.00"),
    ("20", "20"),
    ("1000", "1000"),
    ("0.5", "0.5"),
    ("0.00000000001", "1E-11"),
    ("1234567890123456789012345678901234567890", "1234567890123456789012345678901234567890"),
    ("12345678901234567890.12345678901234567890", "12345678901234567890.12345678901234567890"),
    ("1" + "0" * 63, "1" + "0" * 63),
)

# Refused on read (StoreCorrupt): a stored value that is not plain digits with an optional
# fraction, or is not text at all.
MONEY_READ_REFUSED: tuple[object, ...] = (
    "-0",
    "-1",
    "+1",
    "1_0",
    "1e3",
    "1E+3",
    " 1",
    "1 ",
    "1\n",
    "01",
    "00",
    "00.5",
    ".5",
    "5.",
    "1.2.3",
    "",
    ".",
    "1,000",
    "0x10",
    "NaN",
    "Infinity",
    "١٢",  # Arabic-Indic digits one, two
    "１",  # fullwidth digit one
    "1.٥",  # Arabic-Indic digit in the fraction
    20,
    1.5,
    b"20",
    "1" + "0" * 64,  # 65 characters
    "0." + "0" * 63,  # 65 characters
)

# --- Time ----------------------------------------------------------------------------------

TIME_TEXT_LENGTH = 27

# Value written -> the text stored.
TIME_WRITTEN: tuple[tuple[datetime | float | int, str], ...] = (
    (datetime(2026, 11, 14, 6, 30, 15, 123456, tzinfo=UTC), "2026-11-14T06:30:15.123456Z"),
    (
        datetime(2026, 11, 14, 8, 30, 15, 0, tzinfo=timezone(timedelta(hours=2))),
        "2026-11-14T06:30:15.000000Z",
    ),
    (
        datetime(2026, 1, 1, 0, 15, 0, 5, tzinfo=timezone(timedelta(hours=-5, minutes=-30))),
        "2026-01-01T05:45:00.000005Z",
    ),
    (
        datetime(2024, 2, 29, 23, 30, 0, 0, tzinfo=timezone(timedelta(hours=-1))),
        "2024-03-01T00:30:00.000000Z",
    ),
    (datetime(987, 3, 4, 5, 6, 7, 8, tzinfo=UTC), "0987-03-04T05:06:07.000008Z"),
    (datetime(1, 1, 1, 0, 0, 0, 0, tzinfo=UTC), "0001-01-01T00:00:00.000000Z"),
    (datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=UTC), "9999-12-31T23:59:59.999999Z"),
    (0.0, "1970-01-01T00:00:00.000000Z"),
    (1763101815.5, "2025-11-14T06:30:15.500000Z"),
    (1700000000.123456, "2023-11-14T22:13:20.123456Z"),
    (1700000000, "2023-11-14T22:13:20.000000Z"),
    (-1.5, "1969-12-31T23:59:58.500000Z"),
    (1e-7, "1970-01-01T00:00:00.000000Z"),
    (0.0000014, "1970-01-01T00:00:00.000001Z"),
    (0.0000016, "1970-01-01T00:00:00.000002Z"),
    (253402300799.0, "9999-12-31T23:59:59.000000Z"),
    (-62135596800.0, "0001-01-01T00:00:00.000000Z"),
)

# Refused on write (StoreRefused). None is not here: it is written as NULL.
TIME_WRITE_REFUSED: tuple[object, ...] = (
    datetime(2026, 11, 14, 6, 30, tzinfo=UTC).replace(tzinfo=None),  # naive
    datetime(1, 1, 1, 0, 0, tzinfo=timezone(timedelta(hours=1))),  # before year 1 in UTC
    datetime(9999, 12, 31, 23, 30, tzinfo=timezone(timedelta(hours=-1))),  # after 9999 in UTC
    date(2026, 11, 14),
    "2026-11-14T06:30:15.123456Z",
    True,
    False,
    float("nan"),
    float("inf"),
    float("-inf"),
    253402300800.0,
    -62135596801.0,
    1e18,
    datetime(2026, 11, 14, 6, 30, tzinfo=OddZone(None)),  # naive: its offset is None
    datetime(2026, 11, 14, 6, 30, tzinfo=OddZone(timedelta(hours=24))),  # not a valid offset
    datetime(2026, 11, 14, 6, 30, tzinfo=OddZone(timedelta(hours=-25))),
)

# Text stored -> the aware UTC datetime read.
TIME_READ: tuple[tuple[str, datetime], ...] = (
    ("2026-11-14T06:30:15.123456Z", datetime(2026, 11, 14, 6, 30, 15, 123456, tzinfo=UTC)),
    ("0987-03-04T05:06:07.000008Z", datetime(987, 3, 4, 5, 6, 7, 8, tzinfo=UTC)),
    ("0001-01-01T00:00:00.000000Z", datetime(1, 1, 1, tzinfo=UTC)),
    ("9999-12-31T23:59:59.999999Z", datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=UTC)),
    ("2024-02-29T00:00:00.000000Z", datetime(2024, 2, 29, tzinfo=UTC)),
)

# Refused on read (StoreCorrupt).
TIME_READ_REFUSED: tuple[object, ...] = (
    "2026-11-14T06:30:15.123456",
    "2026-11-14 06:30:15.123456Z",
    "2026-11-14t06:30:15.123456z",
    "2026-11-14T06:30:15Z",
    "2026-11-14T06:30:15.12345Z",
    "2026-11-14T06:30:15.1234567Z",
    "2026-11-14T06:30:15.123456+00:00",
    "2026-11-14T06:30:15,123456Z",
    "2026-13-01T00:00:00.000000Z",
    "2026-02-30T00:00:00.000000Z",
    "2025-02-29T00:00:00.000000Z",
    "2026-11-14T24:00:00.000000Z",
    "2026-11-14T06:60:00.000000Z",
    "2026-11-14T06:30:60.000000Z",
    "0000-01-01T00:00:00.000000Z",
    "٢٠٢٦-11-14T06:30:15.123456Z",  # Arabic-Indic year
    "2026-11-14T06:30:15.123456Z\n",
    " 2026-11-14T06:30:15.123456Z",
    "",
    0,
    1763101815.5,
)

# --- Event detail --------------------------------------------------------------------------

# Mapping given -> the canonical ASCII JSON stored.
DETAIL_WRITTEN: tuple[tuple[dict[str, str | int | None], str], ...] = (
    ({}, "{}"),
    ({"b": 1, "a": "x", "c": None}, '{"a":"x","b":1,"c":null}'),
    ({"k": "café"}, '{"k":"caf\\u00e9"}'),
    ({"café": 0}, '{"caf\\u00e9":0}'),
    ({"k": "bad \ud800"}, '{"k":"bad \\\\ud800"}'),
    ({"n": -5, "big": 2**63 - 1}, '{"big":9223372036854775807,"n":-5}'),
    ({"low": -(2**63)}, '{"low":-9223372036854775808}'),
    ({"q": 'a "quoted" \\ slash'}, '{"q":"a \\"quoted\\" \\\\ slash"}'),
    ({"B": "upper sorts first", "a": ""}, '{"B":"upper sorts first","a":""}'),
)

# Refused on write (StoreRefused).
DETAIL_WRITE_REFUSED: tuple[object, ...] = (
    {"f": 1.5},
    {"f": 0.0},
    {"b": True},
    {"b": False},
    {"l": [1]},
    {"t": (1,)},
    {"d": {}},
    {"by": b"x"},
    {"dec": Decimal(1)},
    {1: "x"},
    {None: "x"},
    [("a", 1)],
    "{}",
    None,
    {"n": 2**63},  # an int outside 64 signed bits
    {"n": -(2**63) - 1},
    {"n": 10**5000},  # past Python's int-to-text digit limit
)

# Refused on read (StoreCorrupt): anything that is not exactly the canonical text of a
# mapping the writer accepts. Every DETAIL_WRITTEN text reads back as its mapping, with the
# one stated exception of the lone-surrogate row, which reads back escaped.
DETAIL_READ_REFUSED: tuple[object, ...] = (
    "",
    "not json",
    "[]",
    '"x"',
    "null",
    '{"a":1.5}',
    '{"a":1e2}',
    '{"a":true}',
    '{"a":NaN}',
    '{"a":[1]}',
    '{"a":{}}',
    '{"a": 1}',
    '{"b":1,"a":2}',
    '{"a":1,"a":2}',
    '{"a":1}\n',
    '{"k":"café"}',
    '{"k":"\\ud800"}',
    5,
    b"{}",
    '{"a":9223372036854775808}',
    '{"a":' + "9" * 5000 + "}",
)
DETAIL_LONE_SURROGATE_READ: tuple[str, dict[str, str]] = (
    '{"k":"bad \\\\ud800"}',
    {"k": "bad \\ud800"},
)
# A mapping that is not a dict is accepted like one.
DETAIL_MAPPING_PROXY: tuple[MappingProxyType[str, str | int | None], str] = (
    MappingProxyType({"b": 1, "a": "x"}),
    '{"a":"x","b":1}',
)
