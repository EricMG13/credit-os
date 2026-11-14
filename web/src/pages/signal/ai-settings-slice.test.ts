// The reader's rules for Topics, the digest form and AI and cost. Expected paths and reasons are
// written out; each case changes the fixture's main scene (AI off) or ai-on in one place.
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
const MAIN = 0;
const AI_ON = 2;
const P = ["snapshot", "settings"];
const M = "scenes[0].snapshot.settings";
const O = "scenes[2].snapshot.settings";

describe("Topics, the digest form and AI and cost in the slice", () => {
  it("reads as the fixture holds them: four topics, one with no keywords; AI off in main, on in ai-on", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error("the fixture reads");
    const [main] = result.data.scenes;
    expect(main.snapshot.settings.topics.map((t) => [t.name, t.keywords.length])).toEqual([
      ["Shipping", 5],
      ["Packaging", 4],
      ["Telecoms", 4],
      ["Rating actions", 0],
    ]);
    expect(result.data.scenes.map((s) => s.snapshot.settings.ai.state).slice(0, 3)).toEqual([
      "off",
      "off",
      "on",
    ]);
  });

  it.each<[string, number, (string | number)[], Json | undefined, string]>([
    [
      "a settings topic listed twice",
      MAIN,
      [...P, "topics", 1, "id"],
      "shipping",
      `${M}.topics[1].id: expected an id the list does not repeat`,
    ],
    [
      "a topic with no kinds list",
      MAIN,
      [...P, "topics", 0, "kinds"],
      undefined,
      `${M}.topics[0].kinds: expected a list`,
    ],
    [
      "a keyword that is a number",
      MAIN,
      [...P, "topics", 1, "keywords", 0],
      4,
      `${M}.topics[1].keywords[0]: expected a string`,
    ],
    [
      "a topic the channel list does not hold",
      MAIN,
      [...P, "topics", 2, "id"],
      "credit",
      `${M}.topics[2].id: expected the id of a topic in the channel list`,
    ],
    [
      "a topic named differently from the channel list",
      MAIN,
      [...P, "topics", 0, "name"],
      "Ships",
      `${M}.topics[0].name: expected the name the channel list gives this topic`,
    ],
    [
      "a channel topic Settings does not list",
      MAIN,
      [...P, "topics"],
      [],
      `${M}.topics: expected a topic for the channel list's "shipping"`,
    ],
    [
      "a covers choice that is not offered",
      MAIN,
      [...P, "digestForm", "covers"],
      "Group: Nobody",
      `${M}.digestForm.covers: expected one of coversOptions`,
    ],
    [
      "no schedule options",
      MAIN,
      [...P, "digestForm", "scheduleOptions"],
      [],
      `${M}.digestForm.scheduleOptions: expected at least one option`,
    ],
    [
      "a repeated length option",
      MAIN,
      [...P, "digestForm", "lengthOptions"],
      ["Up to 5 points", "Up to 5 points"],
      `${M}.digestForm.lengthOptions[1]: expected an option the list does not repeat`,
    ],
    [
      "a brief that is null",
      MAIN,
      [...P, "digestForm", "brief"],
      null,
      `${M}.digestForm.brief: expected a string`,
    ],
    [
      "an AI state that is not a word of the three",
      MAIN,
      [...P, "ai", "state"],
      "paused",
      `${M}.ai.state: expected on, off or capped`,
    ],
    [
      "a notice missing while AI is off",
      MAIN,
      [...P, "ai", "notice"],
      null,
      `${M}.ai.notice: expected the delivered notice`,
    ],
    [
      "a notice shown while AI is on",
      AI_ON,
      [...P, "ai", "notice"],
      { title: "t", text: "x" },
      `${O}.ai.notice: expected null while AI is on`,
    ],
    [
      "a bar position above 1",
      MAIN,
      [...P, "ai", "spend", "position"],
      1.2,
      `${M}.ai.spend.position: expected a number from 0 to 1`,
    ],
    [
      "a bar position below 0",
      AI_ON,
      [...P, "ai", "spend", "position"],
      -0.1,
      `${O}.ai.spend.position: expected a number from 0 to 1`,
    ],
    [
      "a spend label that is a number",
      MAIN,
      [...P, "ai", "spend", "label"],
      6.4,
      `${M}.ai.spend.label: expected a string`,
    ],
    [
      "a repeated part id",
      MAIN,
      [...P, "ai", "parts", 1, "id"],
      "ai-line",
      `${M}.ai.parts[1].id: expected an id the list does not repeat`,
    ],
    [
      "a part on while AI is off",
      MAIN,
      [...P, "ai", "parts", 2, "on"],
      true,
      `${M}.ai.parts[2].on: expected false while AI is off`,
    ],
    [
      "a part whose switch is a string",
      AI_ON,
      [...P, "ai", "parts", 0, "on"],
      "yes",
      `${O}.ai.parts[0].on: expected true or false`,
    ],
  ])("refuses %s", (_name, scene, path, value, reason) => {
    expect(readSlice(change(scene, path, value))).toEqual(invalid(reason));
  });

  it("refuses AI on while a channel digest is paused, and capped with no notice", () => {
    expect(readSlice(change(MAIN, [...P, "ai", "state"], "on"))).toEqual(
      invalid("scenes[0].snapshot.settings.ai.notice: expected null while AI is on"),
    );
    const on = change(MAIN, [...P, "ai", "state"], "on") as { scenes: Members[] };
    const snap = (on.scenes[MAIN]?.snapshot ?? null) as Members;
    ((snap.settings as Members).ai as Members).notice = null;
    expect(readSlice(on)).toEqual(
      invalid(
        "scenes[0].snapshot.channels.digests[0].paused: expected false, as settings.ai.state on says",
      ),
    );
    expect(readSlice(change(AI_ON, [...P, "ai", "state"], "capped"))).toEqual(
      invalid("scenes[2].snapshot.settings.ai.notice: expected the delivered notice"),
    );
  });

  it("refuses AI off while a channel digest is not paused", () => {
    const off = change(AI_ON, [...P, "ai", "state"], "off") as { scenes: Members[] };
    const ai = ((off.scenes[AI_ON]?.snapshot as Members).settings as Members).ai as Members;
    ai.notice = { title: "AI is off", text: "x" };
    for (const part of ai.parts as Members[]) part.on = false;
    expect(readSlice(off)).toEqual(
      invalid(
        "scenes[2].snapshot.channels.digests[0].paused: expected true, as settings.ai.state off says",
      ),
    );
  });

  it("refuses AI off while a story carries a signal strength and no AI line", () => {
    const stale = change(MAIN, ["snapshot", "feed", "stories", 0, "strength"], {
      marks: 2,
      word: "Moderate",
    });
    expect(readSlice(stale)).toEqual(
      invalid(
        "scenes[0].snapshot.feed.stories[0].ai: expected null (and strength null), as settings.ai.state off says",
      ),
    );
  });

  it("refuses AI off while a story carries an AI line", () => {
    const stale = change(MAIN, ["snapshot", "feed", "stories", 0, "ai"], { line: "x" });
    expect(readSlice(stale)).toEqual(
      invalid(
        "scenes[0].snapshot.feed.stories[0].ai: expected null (and strength null), as settings.ai.state off says",
      ),
    );
  });
});
