import {
  address,
  arrayOf,
  at,
  bool,
  child,
  chartInfo as info,
  distinct,
  fail,
  num,
  numOrNull,
  object,
  oneOf,
  text,
  textOrNull,
  type Reader,
} from "./reader-kit";
import { passage } from "./read-analysis";
import { checkStrips, strips } from "./read-portfolio";
import { bridge, checkBridge, checkTicks } from "./read-sections";
import type {
  CaseCard,
  EbitdaPaths,
  ForecastPage,
  GapItem,
  InterestCover,
  RunTab,
  Tick,
} from "./types";

const cells = arrayOf(textOrNull);
const tab = object<RunTab>({ label: text, href: address, count: textOrNull, current: bool });
const pathFields = {
  ...info,
  divider: object({ period: text, at: oneOf(["on", "after"] as const), label: text }),
  yTicks: arrayOf(object<Tick>({ value: num, label: text })),
  head: arrayOf(text),
  rows: arrayOf(object({ label: text, cells })),
};
const interestCover = object<InterestCover>({
  ...pathFields,
  cases: arrayOf(object({ values: arrayOf(numOrNull), labels: cells })),
});
const ebitda = object<EbitdaPaths>({
  ...pathFields,
  series: arrayOf(object({ name: text, values: arrayOf(numOrNull), labels: cells })),
});

export const forecast: Reader<ForecastPage> = object<ForecastPage>({
  tabs: arrayOf(tab),
  periods: arrayOf(text),
  drivers: strips,
  driverKeys: arrayOf(object({ label: text, case: text })),
  interestCover,
  ebitda,
  walk: bridge,
  gap: object<GapItem>({ title: text, reason: text }),
  watch: passage,
  limitations: object({ title: text, text, href: address }),
});

const plural = (n: number, noun: string) => `${String(n)} ${noun}${n === 1 ? "" : "s"}`;

/**
 * The drivers: one marker per case, in case order. The legend words are the first row's names (the
 * mock says "Base case assumption"), so they need not be the case names; every row repeats them.
 */
function checkDrivers(page: ForecastPage, cases: readonly CaseCard[], path: string): void {
  const first = page.drivers.rows[0]?.markers.map((m) => m.name) ?? [];
  page.drivers.rows.forEach((row, i) => {
    const where = `${at(`${path}.rows`, i)}.markers`;
    if (row.markers.length !== cases.length) {
      fail(where, `expected ${plural(cases.length, "marker")}, one per case`);
    }
    row.markers.forEach((m, k) => {
      if (row.markers.findIndex((o) => o.name === m.name) !== k) {
        fail(`${at(where, k)}.name`, "expected a name no other marker has");
      }
      if (m.name !== first[k]) {
        fail(
          `${at(where, k)}.name`,
          `expected the name the first row gives marker ${String(k + 1)}, "${first[k] ?? ""}"`,
        );
      }
      // The page dims a case's marker by its position in the track, so a row has all or none.
      if ((m.value === null) !== (row.markers[0]?.value === null)) {
        fail(
          `${at(where, k)}.value`,
          "expected every marker of a row present, or every one missing",
        );
      }
    });
  });
  // The table's last columns are the cases, in order: a swapped head would put each case's
  // figures under the other's name.
  const head = page.drivers.head;
  if (head.length < cases.length) {
    fail(`${path}.head`, `expected ${plural(cases.length, "case column")} at its end`);
  }
  cases.forEach((c, k) => {
    const column = head.length - cases.length + k;
    if (head[column] !== c.name) {
      fail(at(`${path}.head`, column), `expected the name of case ${String(k + 1)}, "${c.name}"`);
    }
  });
  checkStrips(page.drivers, path, false);
}

/**
 * Legend entry k names the case that marker k belongs to. The page emphasises the chosen case's
 * marker by its position, so entry k must be case k and worded as the markers are.
 */
function checkDriverKeys(page: ForecastPage, cases: readonly CaseCard[], path: string): void {
  const where = child(path, "driverKeys");
  if (page.driverKeys.length !== cases.length) {
    fail(where, `expected ${String(cases.length)} entries, one per case`);
  }
  const labels = page.drivers.rows[0]?.markers.map((m) => m.name) ?? [];
  page.driverKeys.forEach((key, k) => {
    const name = cases[k]?.name ?? "";
    if (key.case !== name) {
      fail(`${at(where, k)}.case`, `expected the name of case ${String(k + 1)}, "${name}"`);
    }
    if (key.label !== labels[k]) {
      fail(
        `${at(where, k)}.label`,
        `expected the name the markers give marker ${String(k + 1)}, "${labels[k] ?? ""}"`,
      );
    }
  });
}

type Block = InterestCover | EbitdaPaths;
type Line = { values: (number | null)[]; labels: (string | null)[] };

/**
 * What both line charts share: ticks, divider, the table's columns and rows (`lines` of them),
 * then each line against its row. `strict` is the interest cover rule: a table cell is `null`
 * exactly where its point is. The EBITDA downside line starts later than its table row, so
 * there a point needs a cell but a cell needs no point.
 */
function checkBlock(
  block: Block,
  lines: readonly Line[],
  names: { line: string; row: string },
  periods: readonly string[],
  strict: boolean,
  cases: readonly CaseCard[],
  path: string,
): void {
  const axisEnd = checkTicks(block.yTicks, `${path}.yTicks`);
  const { divider } = block;
  if (!periods.includes(divider.period))
    fail(`${path}.divider.period`, "expected one of the periods");
  if (divider.at === "after" && divider.period === periods[periods.length - 1]) {
    fail(`${path}.divider`, `expected a period after ${divider.period}`);
  }
  if (block.head.slice(1).join("\u0000") !== periods.join("\u0000")) {
    fail(`${path}.head`, "expected the periods after the first heading, in order");
  }
  if (block.rows.length !== lines.length) {
    fail(`${path}.rows`, `expected ${plural(lines.length, "row")}, one per ${names.row}`);
  }
  distinct(block.rows, (r) => r.label, `${path}.rows`, "label", "row");
  block.rows.forEach((row, k) => {
    const name = cases[k]?.name ?? "";
    if (row.label !== name) {
      fail(
        `${at(`${path}.rows`, k)}.label`,
        `expected the name of case ${String(k + 1)}, "${name}"`,
      );
    }
  });
  block.rows.forEach((row, k) => {
    if (row.cells.length !== periods.length) {
      fail(
        `${at(`${path}.rows`, k)}.cells`,
        `expected ${plural(periods.length, "cell")}, one per period`,
      );
    }
  });
  lines.forEach((line, k) => {
    const where = at(names.line, k);
    const entries = `expected ${String(periods.length)} ${periods.length === 1 ? "entry" : "entries"}, one per period`;
    if (line.values.length !== periods.length) fail(`${where}.values`, entries);
    if (line.labels.length !== periods.length) fail(`${where}.labels`, entries);
    line.values.forEach((value, p) => {
      const label = line.labels[p] ?? null;
      const cell = block.rows[k]?.cells[p] ?? null;
      const cellAt = `${at(`${path}.rows`, k)}.cells[${String(p)}]`;
      if (value === null) {
        if (label !== null) fail(at(`${where}.labels`, p), "expected null beside a missing value");
        if (strict && cell !== null) {
          fail(cellAt, "expected null exactly where the point is missing");
        }
        return;
      }
      if (!(value >= 0 && value <= axisEnd)) {
        fail(
          at(`${where}.values`, p),
          `expected a position within the axis (0 to ${String(axisEnd)})`,
        );
      }
      if (cell === null) {
        fail(
          cellAt,
          strict
            ? "expected null exactly where the point is missing"
            : "expected a cell beside a present point",
        );
      }
      if (label !== null && label !== cell) {
        fail(at(`${where}.labels`, p), "expected the table's text for this point");
      }
    });
  });
  // A period with a cell on any row has a point on some line: the chart draws "n.a." for a
  // period with no point, and the table must not state a figure there.
  if (!strict) {
    periods.forEach((_, p) => {
      const row = block.rows.findIndex((r) => r.cells[p] !== null && r.cells[p] !== undefined);
      if (row !== -1 && lines.every((line) => line.values[p] === null)) {
        fail(
          `${at(`${path}.rows`, row)}.cells[${String(p)}]`,
          "expected a point on some line in a period that has a cell",
        );
      }
    });
  }
}

/** Every rule the page and its charts enforce, so a slice that reads ok never throws there. */
export function checkForecast(page: ForecastPage, cases: readonly CaseCard[], path: string): void {
  const tabs = child(path, "tabs");
  if (page.tabs.filter((t) => t.current).length !== 1) {
    fail(tabs, "expected exactly one current tab");
  }
  distinct(page.tabs, (t) => t.label, tabs, "label", "tab");
  const periods = child(path, "periods");
  if (page.periods.length === 0) fail(periods, "expected at least one period");
  page.periods.forEach((p, i) => {
    if (page.periods.indexOf(p) !== i) fail(at(periods, i), "expected a period no other has");
  });
  checkDrivers(page, cases, child(path, "drivers"));
  checkDriverKeys(page, cases, path);

  const cover = child(path, "interestCover");
  if (page.interestCover.cases.length !== cases.length) {
    fail(`${cover}.cases`, `expected ${plural(cases.length, "line")}, one per case`);
  }
  checkBlock(
    page.interestCover,
    page.interestCover.cases,
    { line: `${cover}.cases`, row: "case" },
    page.periods,
    true,
    cases,
    cover,
  );

  const paths = child(path, "ebitda");
  const { series } = page.ebitda;
  if (series.length !== cases.length) {
    fail(`${paths}.series`, `expected ${plural(cases.length, "line")}, one per case`);
  }
  distinct(series, (s) => s.name, `${paths}.series`, "name", "line");
  checkBlock(
    page.ebitda,
    series,
    { line: `${paths}.series`, row: "line" },
    page.periods,
    false,
    cases,
    paths,
  );

  checkBridge(page.walk, cases, child(path, "walk"));

  // Every title that names a trace control: no two controls on the page share a name.
  const named = new Set(cases.filter((c) => c.trace !== null).map((c) => c.name));
  const items = [
    { name: page.drivers.title, trace: page.drivers.trace, where: "drivers.title" },
    {
      name: page.interestCover.title,
      trace: page.interestCover.trace,
      where: "interestCover.title",
    },
    { name: page.ebitda.title, trace: page.ebitda.trace, where: "ebitda.title" },
    { name: page.walk.title, trace: page.walk.trace, where: "walk.title" },
    { name: page.watch.title, trace: page.watch.trace, where: "watch.title" },
  ];
  for (const item of items) {
    if (item.trace === null) continue;
    if (named.has(item.name)) {
      fail(child(path, item.where), "expected a name no other trace control on the page has");
    }
    named.add(item.name);
  }
}
