// The digests of a snapshot: their issues, points and stories, and the references between the
// digests, the channel list and the feed's digest cards. Expected paths and reasons are written out.
import fixture from "../../../fixtures/signal.json";
import { readSlice } from "./slice";

type Json = { [key: string]: Json } | Json[] | string | number | boolean | null;
type Members = { [key: string]: Json };

const MAIN = 0;
const AI_ON = 2;

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
const AI = "scenes[2].snapshot";
const POINT = `${AI}.digests[0].issues[0].points[0]`;
const P0 = ["snapshot", "digests", 0, "issues", 0, "points", 0];

describe("the digests of a snapshot", () => {
  it("reads as the fixture holds them: both paused in main, neither in ai-on", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error("the fixture reads");
    const sentence = (id: string) =>
      result.data.scenes
        .find((s) => s.id === id)
        ?.snapshot.digests.map((d) => [d.id, d.paused !== null] as const);
    expect(sentence("main")).toEqual([
      ["weekly-brief", true],
      ["daily-ratings", true],
    ]);
    expect(sentence("ai-on")).toEqual([
      ["weekly-brief", false],
      ["daily-ratings", false],
    ]);
  });

  it.each([
    [
      "a point whose number is not a string",
      AI_ON,
      [...P0, "number"],
      3,
      `${POINT}.number: expected a string`,
    ],
    [
      "a point with no stories list",
      AI_ON,
      [...P0, "stories"],
      undefined,
      `${POINT}.stories: expected a list`,
    ],
    [
      "a story whose url is a number",
      AI_ON,
      [...P0, "stories", 1, "url"],
      7,
      `${POINT}.stories[1].url: expected a string or null`,
    ],
    [
      "a story with no source",
      AI_ON,
      [...P0, "stories", 0, "source"],
      undefined,
      `${POINT}.stories[0].source: expected a string`,
    ],
    [
      "a nothing-material issue that still has points",
      AI_ON,
      ["snapshot", "digests", 1, "issues", 1, "points"],
      [{ number: "1", lead: "One", body: null, stories: [] }],
      `${AI}.digests[1].issues[1].points: expected no points on a nothing-to-report issue`,
    ],
    [
      "a nothing-material issue marked AI",
      AI_ON,
      ["snapshot", "digests", 1, "issues", 1, "ai"],
      true,
      `${AI}.digests[1].issues[1].ai: expected false on a nothing-to-report issue`,
    ],
    [
      "a digest id another digest uses",
      AI_ON,
      ["snapshot", "digests", 1, "id"],
      "weekly-brief",
      `${AI}.digests[1].id: expected an id no other digest uses`,
    ],
    [
      "an issue id its digest already uses",
      AI_ON,
      ["snapshot", "digests", 0, "issues", 1, "id"],
      "week-13-nov",
      `${AI}.digests[0].issues[1].id: expected an id the digest does not already use`,
    ],
    [
      "a channel naming no digest",
      AI_ON,
      ["snapshot", "channels", "digests", 1, "id"],
      "ghost",
      `${AI}.channels.digests[1].id: expected the id of a digest in the snapshot's digests`,
    ],
    [
      "a digest the channel list lacks",
      AI_ON,
      ["snapshot", "digests", 2],
      { id: "extra", name: "Extra", paused: null, issues: [] },
      `${AI}.digests[2].id: expected the id of a digest in the channel list`,
    ],
    [
      "a digest named other than its channel",
      AI_ON,
      ["snapshot", "digests", 0, "name"],
      "Monthly brief",
      `${AI}.digests[0].name: expected the name the channel list gives this digest`,
    ],
    [
      "a paused channel whose digest holds no sentence",
      MAIN,
      ["snapshot", "digests", 0, "paused"],
      null,
      "scenes[0].snapshot.digests[0].paused: expected the delivered sentence, as the channel list marks the digest paused",
    ],
    [
      "a digest with a sentence whose channel is not paused",
      AI_ON,
      ["snapshot", "digests", 0, "paused"],
      "Paused.",
      `${AI}.digests[0].paused: expected null, as the channel list marks the digest not paused`,
    ],
    [
      "a feed card naming no digest",
      AI_ON,
      ["snapshot", "feed", "digests", 0, "digestId"],
      "ghost",
      `${AI}.feed.digests[0].digestId: expected the id of a digest in the snapshot's digests`,
    ],
    [
      "a feed card naming an issue of another digest",
      AI_ON,
      ["snapshot", "feed", "digests", 1, "issueId"],
      "week-13-nov",
      `${AI}.feed.digests[1].issueId: expected the id of an issue of the digest the card names`,
    ],
    [
      "a feed card with no digestId",
      AI_ON,
      ["snapshot", "feed", "digests", 0, "digestId"],
      undefined,
      `${AI}.feed.digests[0].digestId: expected a string`,
    ],
    [
      "a card point whose number is missing",
      AI_ON,
      ["snapshot", "feed", "digests", 0, "points", 0, "number"],
      undefined,
      `${AI}.feed.digests[0].points[0].number: expected a string`,
    ],
    [
      "a snapshot with no digests list",
      AI_ON,
      ["snapshot", "digests"],
      undefined,
      `${AI}.digests: expected a list`,
    ],
  ])("rejects %s, naming its path", (_name, scene, path, value, reason) => {
    expect(readSlice(change(scene, path, value as Json | undefined))).toEqual(invalid(reason));
  });

  it("looks digests up by value: ids such as constructor are no special case", () => {
    const slice = change(AI_ON, ["snapshot", "feed", "digests", 0, "digestId"], "constructor");
    expect(readSlice(slice)).toEqual(
      invalid(
        `${AI}.feed.digests[0].digestId: expected the id of a digest in the snapshot's digests`,
      ),
    );
  });
});
