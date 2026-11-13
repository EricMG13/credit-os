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
