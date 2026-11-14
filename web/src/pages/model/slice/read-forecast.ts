import {
  address,
  arrayOf,
  at,
  bool,
  child,
  distinct,
  fail,
  object,
  text,
  textOrNull,
  type Reader,
} from "./reader-kit";
import { passage } from "./read-analysis";
import { checkStrips, strips } from "./read-portfolio";
import type { CaseCard, ForecastPage, GapItem, RunTab } from "./types";

const tab = object<RunTab>({ label: text, href: address, count: textOrNull, current: bool });

export const forecast: Reader<ForecastPage> = object<ForecastPage>({
  tabs: arrayOf(tab),
  periods: arrayOf(text),
  drivers: strips,
  driverKeys: arrayOf(object({ label: text, case: text })),
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

  // Every title that names a trace control: no two controls on the page share a name.
  const named = new Set(cases.filter((c) => c.trace !== null).map((c) => c.name));
  const items = [
    { name: page.drivers.title, trace: page.drivers.trace, where: "drivers.title" },
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
