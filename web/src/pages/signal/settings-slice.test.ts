// The reader's rules for Settings: groups with their visibility, thread rules, notification events,
// and how Settings' groups relate to the channel list's. Expected paths and reasons are written out.
import fixture from "../../../fixtures/signal.json";
import { readSlice } from "./slice";

type Json = { [key: string]: Json } | Json[] | string | number | boolean | null;
type Members = { [key: string]: Json };

const MAIN = 0;
const S = "scenes[0].snapshot.settings";

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
const P = ["snapshot", "settings"];

describe("the settings of a snapshot", () => {
  it("reads as the fixture holds them: three groups, one without members; four rules; four events", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error("the fixture reads");
    const main = result.data.scenes[0].snapshot.settings;
    expect(main.groups.map((g) => [g.name, g.members.length, g.visibility])).toEqual([
      ["Leveraged credit", 4, "Visible to everyone"],
      ["Shipping desk", 3, "Members only"],
      ["Committee prep", 0, "Members only"],
    ]);
    expect(main.rules.map((r) => r.on)).toEqual([true, true, false, true]);
    expect(main.notifications.events).toHaveLength(4);
  });

  it.each([
    [
      "a rule whose switch is a string",
      [...P, "rules", 0, "on"],
      "true",
      `${S}.rules[0].on: expected true or false`,
    ],
    [
      "a rule with no label",
      [...P, "rules", 1, "label"],
      undefined,
      `${S}.rules[1].label: expected a string`,
    ],
    [
      "an event whose desktop switch is a number",
      [...P, "notifications", "events", 2, "onDesktop"],
      1,
      `${S}.notifications.events[2].onDesktop: expected true or false`,
    ],
    [
      "a group whose members are not a list",
      [...P, "groups", 0, "members"],
      "none",
      `${S}.groups[0].members: expected a list`,
    ],
    [
      "a visibility the group does not offer",
      [...P, "groups", 0, "visibility"],
      "Everyone",
      `${S}.groups[0].visibility: expected one of the group's visibilityOptions`,
    ],
    [
      "no visibility options",
      [...P, "groups", 1, "visibilityOptions"],
      [],
      `${S}.groups[1].visibilityOptions: expected at least one option`,
    ],
    [
      "a repeated visibility option",
      [...P, "groups", 1, "visibilityOptions"],
      ["Members only", "Members only"],
      `${S}.groups[1].visibilityOptions[1]: expected an option the list does not repeat`,
    ],
    [
      "a +N with no members shown",
      [...P, "groups", 2, "moreMembers"],
      "+2",
      `${S}.groups[2].moreMembers: expected null when the group lists no members`,
    ],
    [
      "a repeated group id",
      [...P, "groups", 1, "id"],
      "leveraged-credit",
      `${S}.groups[1].id: expected an id the list does not repeat`,
    ],
    [
      "a repeated rule id",
      [...P, "rules", 3, "id"],
      "comments-edited",
      `${S}.rules[3].id: expected an id the list does not repeat`,
    ],
    [
      "a repeated event id",
      [...P, "notifications", "events", 1, "id"],
      "comment",
      `${S}.notifications.events[1].id: expected an id the list does not repeat`,
    ],
    [
      "a group named differently from the channel list",
      [...P, "groups", 1, "name"],
      "Shipping team",
      `${S}.groups[1].name: expected the name the channel list gives this group`,
    ],
  ])("refuses %s", (_what, path, value, reason) => {
    expect(readSlice(change(MAIN, path, value as Json | undefined))).toEqual(invalid(reason));
  });

  it("refuses a channel group that Settings does not list", () => {
    const result = readSlice(change(MAIN, [...P, "groups"], []));
    expect(result).toEqual(
      invalid(
        "scenes[0].snapshot.channels.groups[0].id: expected the id of a group in settings.groups",
      ),
    );
  });

  it("refuses a snapshot with no settings", () => {
    expect(readSlice(change(MAIN, P, undefined))).toEqual(
      invalid("scenes[0].snapshot.settings: expected an object"),
    );
  });

  it("accepts a Settings group the channel list does not hold", () => {
    expect(readSlice(fixture.slice).kind).toBe("ok");
  });
});
