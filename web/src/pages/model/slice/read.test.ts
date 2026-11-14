import { readSlice } from "./read";
import { edited, fixtureSlice } from "./test-fixture";

const RUN = ["runs", 0] as const;

describe("readSlice", () => {
  it("is absent when the data file holds no model member", () => {
    expect(readSlice(undefined)).toEqual({ kind: "absent" });
  });

  it("reads the fixture", () => {
    const result = readSlice(fixtureSlice());
    if (result.kind !== "ok") throw new Error(result.kind);
    expect(result.data.runs[0]?.header.issuerName).toBe("TransDigm Group");
    expect(result.data.runs[0]?.limitations.items).toHaveLength(6);
    expect(result.data.runs[0]?.limitations.items[0]?.trace).toBe(
      "#/library/transdigm/2025-06-30/evidence",
    );
  });

  it("refuses a second run for the same issuer and run, naming the repeat", () => {
    const source = fixtureSlice() as { runs: unknown[] };
    source.runs.push(structuredClone(source.runs[0]));
    expect(readSlice(source)).toEqual({
      kind: "invalid",
      reason: "runs[1].run: expected a run no other run has",
    });
  });

  it("accepts a second run of the same issuer on another date", () => {
    const source = fixtureSlice() as { runs: { run: string }[] };
    const other = structuredClone(source.runs[0]) as { run: string };
    other.run = "2024-12-31";
    source.runs.push(other);
    expect(readSlice(source).kind).toBe("ok");
  });

  it("keeps a null trace as null", () => {
    const result = readSlice(edited([...RUN, "limitations", "items", 1, "trace"], null));
    if (result.kind !== "ok") throw new Error(result.kind);
    expect(result.data.runs[0]?.limitations.items[1]?.trace).toBeNull();
  });

  it.each([
    ["not an object", edited([], 5), "slice: expected an object"],
    ["the slice with an extra key", edited(["extra"], 1), "extra: unknown field"],
    ["a run with an extra key", edited([...RUN, "extra"], 1), "runs[0].extra: unknown field"],
    ["a run list that is no list", edited(["runs"], {}), "runs: expected a list"],
    ["a run missing a key", edited([...RUN, "run"], undefined), "runs[0].run: missing"],
    [
      "a header flag that is no boolean",
      edited([...RUN, "header", "sample"], "yes"),
      "runs[0].header.sample: expected true or false",
    ],
    [
      "a header state the Run states set lacks",
      edited([...RUN, "header", "state"], "Done"),
      "runs[0].header.state: expected one of Queued, Running, Finished, Failed, Capped, Rejected, Interrupted",
    ],
    [
      "a link that is no string",
      edited([...RUN, "links", "report"], 3),
      "runs[0].links.report: expected a string",
    ],
    [
      "limitations with a null count",
      edited([...RUN, "limitations", "count"], null),
      "runs[0].limitations.count: expected a string",
    ],
    [
      "a limitation with a numeric trace",
      edited([...RUN, "limitations", "items", 2, "trace"], 4),
      "runs[0].limitations.items[2].trace: expected a string or null",
    ],
    [
      "a gap missing its reason",
      edited([...RUN, "limitations", "notEstablished", "items", 1, "reason"], undefined),
      "runs[0].limitations.notEstablished.items[1].reason: missing",
    ],
    [
      "a gap group with a numeric count",
      edited([...RUN, "limitations", "notEstablished", "count"], 3),
      "runs[0].limitations.notEstablished.count: expected a string",
    ],
  ])("is invalid and names the failing path: %s", (_, source, reason) => {
    expect(readSlice(source)).toEqual({ kind: "invalid", reason });
  });
});

const TRACE_REPEAT = "expected a name no other trace control on the page has";

describe("readSlice: no two trace controls on a page share a name (front, limitations, statements)", () => {
  it.each([
    [
      "a limitation titled as an earlier limitation",
      edited([...RUN, "limitations", "items", 1, "title"], "EBITDA is the company’s own measure"),
      "runs[0].limitations.items[1].title",
    ],
  ])("refuses %s, naming the second one", (_, source, where) => {
    expect(readSlice(source)).toEqual({ kind: "invalid", reason: `${where}: ${TRACE_REPEAT}` });
  });
});

describe("readSlice: lists the pages draw hold something", () => {
  it.each([
    [
      "no limitation",
      edited([...RUN, "limitations", "items"], []),
      "runs[0].limitations.items: expected at least one limitation",
    ],
  ])("refuses %s", (_, source, reason) => {
    expect(readSlice(source)).toEqual({ kind: "invalid", reason });
  });

  it("reads a run with nothing yet to report as not established, which the page draws as its heading and count", () => {
    const result = readSlice(edited([...RUN, "limitations", "notEstablished", "items"], []));
    expect(result.kind).toBe("ok");
  });
});

describe("readSlice: a string the page draws is never empty", () => {
  const P = "runs[0]";
  const NON_EMPTY = "expected a non-empty string";
  it.each([
    [["issuer"], `${P}.issuer`],
    [["run"], `${P}.run`],
    [["header", "issuerName"], `${P}.header.issuerName`],
    [["header", "asOf"], `${P}.header.asOf`],
    [["header", "purpose"], `${P}.header.purpose`],
    [["limitations", "count"], `${P}.limitations.count`],
    [["limitations", "gapsLinkText"], `${P}.limitations.gapsLinkText`],
    [["limitations", "lead"], `${P}.limitations.lead`],
    [["limitations", "items", 0, "title"], `${P}.limitations.items[0].title`],
    [["limitations", "items", 0, "label"], `${P}.limitations.items[0].label`],
    [["limitations", "items", 0, "text"], `${P}.limitations.items[0].text`],
    [["limitations", "notEstablished", "count"], `${P}.limitations.notEstablished.count`],
    [
      ["limitations", "notEstablished", "items", 0, "title"],
      `${P}.limitations.notEstablished.items[0].title`,
    ],
    [
      ["limitations", "notEstablished", "items", 0, "reason"],
      `${P}.limitations.notEstablished.items[0].reason`,
    ],
  ] as [(string | number)[], string][])("refuses an empty string at %j", (steps, where) => {
    expect(readSlice(edited([...RUN, ...steps], ""))).toEqual({
      kind: "invalid",
      reason: `${where}: ${NON_EMPTY}`,
    });
  });
});

describe("readSlice: an address into the library starts with #/", () => {
  const P = "runs[0]";
  const OFF = 'expected an address starting with "#/"';
  it.each([
    [["links", "report"], `${P}.links.report`, "https://example.invalid/x"],
    [["links", "evidence"], `${P}.links.evidence`, "//example.invalid/x"],
    [["links", "library"], `${P}.links.library`, "library/transdigm"],
    [["links", "evidenceGaps"], `${P}.links.evidenceGaps`, "/#/x"],
    [
      ["limitations", "items", 0, "trace"],
      `${P}.limitations.items[0].trace`,
      "ftp://example.invalid",
    ],
  ] as [(string | number)[], string, string][])("refuses %j holding %s", (steps, where, value) => {
    expect(readSlice(edited([...RUN, ...steps], value))).toEqual({
      kind: "invalid",
      reason: `${where}: ${OFF}`,
    });
  });
});
