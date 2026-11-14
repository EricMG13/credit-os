import { cx } from "./cx";

describe("cx", () => {
  it("keeps a type-scale class beside a text colour", () => {
    expect(cx("text-small text-text-link")).toBe("text-small text-text-link");
  });

  it("keeps only the last of two text colours", () => {
    expect(cx("text-small text-body")).toBe("text-body");
  });
});
