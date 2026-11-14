// The reader's rules for Settings' sources, and how they agree with the feed's own claims about
// sources. Expected paths and reasons are written out; the fixture is main's five sources.
import fixture from "../../../fixtures/signal.json";
import { readSlice } from "./slice";

type Json = { [key: string]: Json } | Json[] | string | number | boolean | null;
type Members = { [key: string]: Json };

/** A copy of the fixture slice with scene `scene` changed at `path` (`undefined` deletes the member). */
function change(scene: number, path: (string | number)[], value: Json | undefined): unknown {
  const copy = structuredClone(fixture.slice) as { scenes: Json[] };
  let at: Json = copy.scenes[scene] ?? null;
  for (const step of path.slice(0, -1)) at = (at as Members)[step] ?? null;
  const last = path[path.length - 1] ?? "";
  if (value === undefined) Reflect.deleteProperty(at as Members, last);
  else (at as Members)[last] = value;
  return copy;
}
const invalid = (reason: string) => ({ kind: "invalid", reason });
const P = ["snapshot", "settings", "sources"];
const S = "scenes[0].snapshot.settings.sources";

describe("the sources of a snapshot", () => {
  it("reads as the fixture holds them: five sources, six states between them, six weeks each", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error("the fixture reads");
    const { sources } = result.data.scenes[0].snapshot.settings;
    expect(sources.map((s) => [s.name, s.state, s.health])).toEqual([
      ["Harbour Wire", "Approved", "Healthy"],
      ["Regulatory Gazette", "Approved", "Quiet"],
      ["Northgate Ratings", "Approved", "Failing"],
      ["The Meridian Post", "Paused", null],
      ["Freight Monitor", "Proposed", null],
    ]);
    expect(sources.map((s) => s.weeks.length)).toEqual([6, 6, 6, 6, 0]);
  });

  it.each([
    [
      "a state outside the three",
      [...P, 0, "state"],
      "Retired",
      `${S}[0].state: expected Proposed, Approved or Paused`,
    ],
    [
      "a health outside the three",
      [...P, 0, "health"],
      "Fine",
      `${S}[0].health: expected Healthy, Quiet, Failing or null`,
    ],
    [
      "a proposed source with a health",
      [...P, 4, "health"],
      "Healthy",
      `${S}[4].health: expected null for a proposed source`,
    ],
    [
      "a reason on a source that is not failing",
      [...P, 0, "reason"],
      "It failed",
      `${S}[0].reason: expected a reason exactly when the health is Failing`,
    ],
    [
      "a failing source with no reason",
      [...P, 2, "reason"],
      null,
      `${S}[2].reason: expected a reason exactly when the health is Failing`,
    ],
    [
      "a health note on a source with no health",
      [...P, 3, "healthNote"],
      "Quiet since May",
      `${S}[3].healthNote: expected null when the source has no health`,
    ],
    [
      "a last item with no last check",
      [...P, 3, "lastCheck"],
      null,
      `${S}[3].lastItem: expected null when there is no last check`,
    ],
    [
      "a week height above 1",
      [...P, 0, "weeks", 2, "height"],
      1.5,
      `${S}[0].weeks[2].height: expected a number from 0 to 1`,
    ],
    [
      "a week height below 0",
      [...P, 0, "weeks", 2, "height"],
      -0.1,
      `${S}[0].weeks[2].height: expected a number from 0 to 1`,
    ],
    [
      "a week with a count and no height",
      [...P, 0, "weeks", 1, "height"],
      null,
      `${S}[0].weeks[1].height: expected both a count and a height, or neither`,
    ],
    [
      "a week with a height and no count",
      [...P, 0, "weeks", 1, "items"],
      null,
      `${S}[0].weeks[1].items: expected both a count and a height, or neither`,
    ],
    [
      "a reading of zero with a bar height",
      [...P, 1, "weeks", 5, "height"],
      0.2,
      `${S}[1].weeks[5].height: expected 0 for a reading of zero`,
    ],
    [
      "a sort rank that is a string",
      [...P, 0, "sort", "health"],
      "first",
      `${S}[0].sort.health: expected a number`,
    ],
    [
      "a repeated source id",
      [...P, 1, "id"],
      "harbour-wire",
      `scenes[0].snapshot.settings.sources[1].id: expected an id the list does not repeat`,
    ],
    [
      "a source with fewer weeks than the others",
      [...P, 1, "weeks"],
      [{ label: "Week of 10 Nov", items: "1", height: 1 }],
      `${S}[1].weeks: expected 6 weeks, as the other sources have`,
    ],
    [
      "a heading that is not a string",
      ["snapshot", "settings", "sourceWeeksHeading"],
      6,
      "scenes[0].snapshot.settings.sourceWeeksHeading: expected a string",
    ],
  ] satisfies [string, (string | number)[], Json | undefined, string][])(
    "rejects %s with its path",
    (_name, path, value, reason) => {
      expect(readSlice(change(0, path, value))).toEqual(invalid(reason));
    },
  );

  it("rejects a feed that says sources are approved when none is listed Approved", () => {
    const path = ["snapshot", "settings", "sources"];
    // scene 8 is no-sources (approved false, empty list): list one Approved source there
    const copy = change(8, path, fixture.slice.scenes[9]?.snapshot.settings.sources);
    expect(readSlice(copy)).toEqual(
      invalid("scenes[8].snapshot.feed.sources.approved: expected true, as settings.sources lists"),
    );
  });

  it("rejects a feed that says sources are approved when the list holds none", () => {
    expect(readSlice(change(1, ["snapshot", "settings", "sources"], []))).toEqual(
      invalid(
        "scenes[1].snapshot.feed.sources.approved: expected false, as settings.sources lists",
      ),
    );
  });

  it("rejects failing sources named by the feed when none is listed Failing", () => {
    const copy = change(1, ["snapshot", "feed", "freshness", "failing"], "1 source failing");
    expect(readSlice(copy)).toEqual(
      invalid(
        "scenes[1].snapshot.feed.freshness.failing: expected null, as settings.sources lists no failing source",
      ),
    );
  });
});
