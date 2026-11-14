import { readFileSync } from "node:fs";
import path from "node:path";
import { readSlice } from "./read";

/**
 * Whole-branch review fix round 1, reader rules (WBR-02 to WBR-07): each case breaks one record of
 * the fixture and expects `invalid` at the exact path. Expected paths are written here, not read
 * from the reader.
 */
type Json = Record<string, unknown>;
type Slice = {
  home: { filters: Record<string, string[]> } & Json;
  issuers: { history: { entries: Json[] }; runs: Json[] }[];
};

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { slice: unknown };

const fresh = () => structuredClone(fixture.slice) as Slice;
/** The first fully loaded run of the first issuer, as a plain record to break. */
const run = (slice: Slice) =>
  slice.issuers[0]?.runs[0] as Json & {
    overview: Json & { limitations: Json; sides: { columns: Json[] } };
    evidence: Json & {
      tabs: Json;
      summary: { take: { download: Json } };
      record: { registers: { rows: Json[] }; hashes: { items: Json[] } };
    };
  };
const RUN = "issuers[0].runs[0]";

function reasonOf(source: unknown): string {
  const result = readSlice(source);
  if (result.kind !== "invalid") throw new Error(`expected invalid, got ${result.kind}`);
  return result.reason;
}

describe("WBR-02 a home figure with blank text", () => {
  it("is refused at the measure's text, as every other drawn figure is", () => {
    const slice = fresh();
    const card = slice.home.cards as { measures: Record<string, Json> }[];
    (card[0]?.measures["netLeverage"] as Json)["text"] = "";
    expect(reasonOf(slice)).toContain("home.cards[0].measures.netLeverage.text");
  });
});

describe("WBR-03 names the pages key by are held unique", () => {
  it("refuses two registers with one name", () => {
    const slice = fresh();
    const rows = run(slice).evidence.record.registers.rows;
    (rows[1] as Json)["name"] = (rows[0] as Json)["name"];
    expect(reasonOf(slice)).toContain(`${RUN}.evidence.record.registers.rows[1].name`);
  });

  it("refuses two hashes with one label", () => {
    const slice = fresh();
    const items = run(slice).evidence.record.hashes.items;
    (items[1] as Json)["label"] = (items[0] as Json)["label"];
    expect(reasonOf(slice)).toContain(`${RUN}.evidence.record.hashes.items[1].label`);
  });

  it.each(["sector", "pathway", "state"])("refuses a %s filter option listed twice", (key) => {
    const slice = fresh();
    const options = slice.home.filters[key] as string[];
    const at = options.length;
    options.push(options[0] as string);
    expect(reasonOf(slice)).toContain(`home.filters.${key}[${String(at)}]`);
  });

  it("refuses two For and against columns with one name", () => {
    const slice = fresh();
    const columns = run(slice).overview.sides.columns;
    (columns[1] as Json)["name"] = (columns[0] as Json)["name"];
    expect(reasonOf(slice)).toContain(`${RUN}.overview.sides.columns[1].name`);
  });
});

describe("WBR-04 a delivered address stays inside the library folder", () => {
  it.each([
    ["an https address", "https://example.invalid/handoffs.zip"],
    ["a javascript address", "javascript:alert(1)"],
    ["a protocol-relative address", "//example.invalid/x.zip"],
    ["a rooted path", "/downloads/x.zip"],
    ["a backslash-rooted path", "\\downloads\\x.zip"],
    ["a drive path", "C:\\downloads\\x.zip"],
    ["a parent segment", "downloads/../../x.zip"],
    ["a backslash parent segment", "downloads\\..\\..\\x.zip"],
    ["a space before https", " https://example.invalid/x.zip"],
    ["a tab before https", "\thttps://example.invalid/x.zip"],
    ["a space before slashes", " //example.invalid/x.zip"],
    ["a newline inside a scheme", "ht\ntps://example.invalid/x.zip"],
    ["a tab between slashes", "\t/\t/example.invalid/x.zip"],
    ["encoded parent segments", "downloads/%2e%2e/%2e%2e/x.zip"],
    ["a half-encoded parent segment", "downloads/.%2E/x.zip"],
    ["a space before a rooted path", " /etc/x"],
    ["an encoded slash", "downloads%2f..%2fx.zip"],
    ["a malformed escape", "downloads/%zz/x.zip"],
  ])("refuses %s as a download", (_, href) => {
    const slice = fresh();
    run(slice).evidence.summary.take.download["href"] = href;
    expect(reasonOf(slice)).toContain(`${RUN}.evidence.summary.take.download.href`);
  });

  it("refuses an address that leaves the library on a register's Open link", () => {
    const slice = fresh();
    (run(slice).evidence.record.registers.rows[0] as Json)["href"] =
      "https://example.invalid/sources.md";
    expect(reasonOf(slice)).toContain(`${RUN}.evidence.record.registers.rows[0].href`);
  });

  it("keeps reading a relative path inside the folder", () => {
    const slice = fresh();
    run(slice).evidence.summary.take.download["href"] = "downloads/a/b-2026.zip";
    expect(readSlice(slice).kind).toBe("ok");
  });
});

describe("WBR-05 a run id an address can carry", () => {
  it("refuses an empty run id at its path", () => {
    const slice = fresh();
    const runs = slice.issuers[0]?.runs as Json[];
    const index = runs.findIndex((r) => r["id"] === "2026-03-31");
    (runs[index] as Json)["id"] = "";
    expect(reasonOf(slice)).toContain(`issuers[0].runs[${String(index)}].id`);
  });
});

describe("WBR-06 a changes link the history page would not draw", () => {
  it("refuses a changes link beside a null report", () => {
    const slice = fresh();
    const entries = slice.issuers[0]?.history.entries as Json[];
    const index = entries.findIndex((e) => e["report"] !== null && e["changes"] !== null);
    expect(index).toBeGreaterThanOrEqual(0);
    (entries[index] as Json)["report"] = null;
    expect(reasonOf(slice)).toContain(`issuers[0].history.entries[${String(index)}].changes`);
  });
});

describe("WBR-07 a count shown beside rows equals the rows held", () => {
  it("refuses a Sources tab count that is not the number of files", () => {
    const slice = fresh();
    run(slice).evidence.tabs["sources"] = "999";
    expect(reasonOf(slice)).toContain(`${RUN}.evidence.tabs.sources`);
  });

  it("refuses a limitations count that is not the number of items", () => {
    const slice = fresh();
    run(slice).overview.limitations["count"] = "40";
    expect(reasonOf(slice)).toContain(`${RUN}.overview.limitations.count`);
  });
});
