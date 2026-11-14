import { readFileSync } from "node:fs";
import path from "node:path";
import { cell, readSlice } from "./read";

type Json = Record<string, unknown>;

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { slice: Json };

/** A deep copy of the fixture's slice that a test can break. */
function fresh(): { home: { cards: Json[]; filters: Json } & Json; issuers: Json[] } {
  return structuredClone(fixture.slice) as ReturnType<typeof fresh>;
}

type Card = Json & { measures: Json };
const cardAt = (slice: ReturnType<typeof fresh>, i: number) => slice.home.cards[i] as Card;

function invalidReason(source: unknown): string {
  const result = readSlice(source);
  if (result.kind !== "invalid") throw new Error(`expected invalid, got ${result.kind}`);
  return result.reason;
}

describe("readSlice", () => {
  it("reads the fixture's slice as ok", () => {
    const result = readSlice(fixture.slice);
    expect(result.kind).toBe("ok");
    if (result.kind === "ok") {
      expect(result.data.home.cards).toHaveLength(6);
      expect(result.data.issuers.map((issuer) => issuer.name)).toContain("Lumora Health");
    }
  });

  it("is absent when the data file has no library member", () => {
    expect(readSlice(undefined)).toEqual({ kind: "absent" });
  });

  it.each([
    ["a slice that is not an object", "text", "slice"],
    ["a missing home", { issuers: [] }, "home"],
  ])("is invalid for %s, naming %s", (_, source, path) => {
    expect(invalidReason(source)).toContain(path);
  });

  it("names the exact path of a malformed card field", () => {
    const slice = fresh();
    slice.home.cards[1] = { ...slice.home.cards[1], note: 7 };
    expect(invalidReason(slice)).toContain("home.cards[1].note");
  });

  it("names the path of a malformed nested progress value", () => {
    const slice = fresh();
    slice.home.cards[2] = {
      ...slice.home.cards[2],
      progress: { text: "6 of 6", value: "6", max: 6 },
    };
    expect(invalidReason(slice)).toContain("home.cards[2].progress.value");
  });

  it("rejects a progress value beyond its max", () => {
    const slice = fresh();
    slice.home.cards[0] = { ...slice.home.cards[0], progress: { text: "x", value: 14, max: 13 } };
    expect(invalidReason(slice)).toContain("home.cards[0].progress.value");
  });

  it("rejects a state outside the run states", () => {
    const slice = fresh();
    slice.home.cards[3] = { ...slice.home.cards[3], state: "Done" };
    expect(invalidReason(slice)).toContain("home.cards[3].state");
  });

  it("rejects an unknown card kind", () => {
    const slice = fresh();
    slice.home.cards[5] = { kind: "other" };
    expect(invalidReason(slice)).toContain("home.cards[5].kind");
  });

  it("rejects a card whose issuer is not in the issuer list", () => {
    const slice = fresh();
    slice.home.cards[0] = { ...slice.home.cards[0], issuer: "nobody" };
    expect(invalidReason(slice)).toContain("home.cards[0].issuer");
  });

  it("rejects an href that is missing rather than null", () => {
    const slice = fresh();
    const noHref = { ...slice.home.cards[0] };
    delete noHref["href"];
    slice.home.cards[0] = noHref;
    expect(invalidReason(slice)).toContain("home.cards[0].href");
  });

  it("rejects a filter list that holds a non-string", () => {
    const slice = fresh();
    slice.home.filters["sector"] = ["Rigid packaging", 3];
    expect(invalidReason(slice)).toContain("home.filters.sector[1]");
  });

  it("requires one applied-count label for zero to seven filters", () => {
    const slice = fresh();
    slice.home.filters["appliedLabels"] = ["No filter applied"];
    expect(invalidReason(slice)).toContain("home.filters.appliedLabels");
  });

  it("names the path of a malformed issuer record", () => {
    const slice = fresh();
    slice.issuers[2] = { id: "tessaly-foods" };
    expect(invalidReason(slice)).toContain("issuers[2].name");
  });

  it("does not read a prototype property as a field", () => {
    const slice = fresh();
    const card = Object.create({ kind: "loading" }) as Json;
    slice.home.cards[5] = card;
    expect(invalidReason(slice)).toContain("home.cards[5].kind");
  });
});

describe("cell", () => {
  const read = (value: unknown) => cell({ c: value }, "c", "row");

  it.each([
    ["missing", null],
    ["a value with a position", { kind: "value", text: "4.2x", at: 4.2 }],
    ["a value without one", { kind: "value", text: "n/m", at: null }],
    ["a withheld value with a reason", { kind: "withheld", reason: "Under embargo" }],
    ["a withheld value without a reason", { kind: "withheld", reason: null }],
    ["a gap", { kind: "gap", reason: "Not in the files provided" }],
  ])("reads %s as written", (_, value) => {
    expect(read(value)).toEqual(value);
  });

  it("does not turn an absent field into missing", () => {
    expect(() => cell({}, "c", "row")).toThrow("row.c");
  });

  it.each([
    ["an unknown kind", { kind: "zero", text: "0" }, "row.c.kind"],
    ["a value with no text", { kind: "value", at: 1 }, "row.c.text"],
    ["a value whose position is a string", { kind: "value", text: "1", at: "1" }, "row.c.at"],
    ["a gap with no reason", { kind: "gap", reason: null }, "row.c.reason"],
    ["a number where a cell belongs", 0, "row.c"],
  ])("rejects %s at its path", (_, value, where) => {
    expect(() => read(value)).toThrow(where);
  });
});

describe("readSlice, the List side", () => {
  it("names the path of a malformed measure figure", () => {
    const slice = fresh();
    const card = cardAt(slice, 0);
    card.measures = { ...card.measures, netLeverage: { text: "2.9x", at: "2.9" } };
    expect(invalidReason(slice)).toContain("home.cards[0].measures.netLeverage.at");
  });

  it("rejects a basis that is neither reported nor adjusted", () => {
    const slice = fresh();
    const card = cardAt(slice, 2);
    card.measures = {
      ...card.measures,
      leverage: { text: "5.6x", at: 5.6, basis: "estimated", description: "x" },
    };
    expect(invalidReason(slice)).toContain("home.cards[2].measures.leverage.basis");
  });

  it("takes an explicit null measure as not recorded, and an absent one as malformed", () => {
    const slice = fresh();
    expect(cardAt(slice, 4).measures).toMatchObject({ leverage: null, netLeverage: null });
    delete cardAt(slice, 4).measures.leverage;
    expect(invalidReason(slice)).toContain("home.cards[4].measures.leverage");
  });

  it("names the path of a band whose range is reversed, and of a missing list", () => {
    const slice = fresh();
    const specs = (slice.home as unknown as { list: { measures: Record<string, Json> } }).list
      .measures;
    specs.leverage = {
      ...specs.leverage,
      bands: [{ label: "Bad", min: 5, max: 3 }],
    };
    expect(invalidReason(slice)).toContain("home.list.measures.leverage.bands[0].max");
    specs.leverage = {
      ...specs.leverage,
      bands: [
        { label: "Low", min: null, max: 3 },
        { label: "Low", min: 3, max: null },
      ],
    };
    expect(invalidReason(slice)).toContain("home.list.measures.leverage.bands[1].label");
    const bare = fresh();
    delete (bare.home as Json).list;
    expect(invalidReason(bare)).toContain("home.list");
  });
});
