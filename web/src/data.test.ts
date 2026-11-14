import { readLibraryData } from "./data";

describe("readLibraryData", () => {
  it("reports missing data when nothing was loaded", () => {
    expect(readLibraryData(undefined)).toEqual({ kind: "missing" });
  });

  it("reports a newer schema", () => {
    expect(readLibraryData({ schema: "credit-os-data/2", issuers: [] })).toEqual({
      kind: "newer",
      schema: "credit-os-data/2",
    });
  });

  it("accepts the known schema", () => {
    expect(
      readLibraryData({
        schema: "credit-os-data/1",
        issuers: [{ id: "tdg", name: "TransDigm" }],
      }),
    ).toEqual({
      kind: "ok",
      data: { schema: "credit-os-data/1", issuers: [{ id: "tdg", name: "TransDigm" }] },
    });
  });

  it("treats a malformed object as missing", () => {
    expect(readLibraryData({ schema: "credit-os-data/1", issuers: "x" })).toEqual({
      kind: "missing",
    });
  });
});

describe("readLibraryData page group members", () => {
  const base = { schema: "credit-os-data/1", issuers: [] };

  it("copies a group's member through unchanged when the source has it", () => {
    const result = readLibraryData({ ...base, library: { a: 1 }, run: [], signal: null });
    expect(result.kind === "ok" && result.data).toEqual({
      ...base,
      library: { a: 1 },
      run: [],
      signal: null,
    });
  });

  it("leaves a member absent, not undefined or empty, when the source lacks it", () => {
    const result = readLibraryData({ ...base, model: undefined });
    if (result.kind !== "ok") throw new Error("expected ok");
    expect(Object.keys(result.data)).toEqual(["schema", "issuers"]);
  });
});
