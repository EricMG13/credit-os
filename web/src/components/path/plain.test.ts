import { describe, expect, it } from "vitest";
import { plainSegment } from "./plain";

describe("plainSegment", () => {
  it.each(["run-1", "a.b", "Issuer_Name~1", "x@y+z=1,2", "a%20b", "%41", "a%7Eb", "%20"])(
    "accepts %s",
    (s) => {
      expect(plainSegment(s)).toBe(true);
    },
  );

  it.each([
    ["dot", "."],
    ["dot dot", ".."],
    ["encoded dot", "%2e"],
    ["encoded dot dot", "%2e%2E"],
    ["encoded slash", "%2F"],
    ["encoded backslash", "%5C"],
    ["bad escape", "%E0%A4%A"],
    ["non-UTF-8 escape", "%E0%A4"],
    ["empty segment", ""],
    ["space", "a b"],
    ["colon", "c:"],
    ["bare percent", "100%"],
    ["NUL escape", "a%00b"],
    ["low control escape, lower case", "a%1fb"],
    ["low control escape, upper case", "a%1Fb"],
    ["DEL escape, lower case", "a%7fb"],
    ["DEL escape, upper case", "a%7Fb"],
    ["tab escape", "%09"],
  ])("refuses %s", (_name, s) => {
    expect(plainSegment(s)).toBe(false);
  });
});
