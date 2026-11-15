// Shared set-up for the Signal page and slice tests: render the app on the Signal fixture, the page
// query, the settle wait and the fixture copy helpers. Test-only: no test's expected value lives here.
import { act, render, within } from "@testing-library/react";
import fixture from "../../../fixtures/signal.json";
import { App } from "../../App";
import type { LoadResult } from "../../data";

export type Json = { [key: string]: Json } | Json[] | string | number | boolean | null;
export type Members = { [key: string]: Json };
export type Scene = (typeof fixture.slice.scenes)[number];

/** Renders the app at `hash` with `slice` (the fixture's own unless a test passes a changed copy). */
export function show(hash: string, slice: unknown = fixture.slice) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], signal: slice },
  };
  return render(<App result={result} />);
}

/** Queries within the Signal page itself, without the channel list beside it. */
export const page = () => within(document.getElementById("signal-content") as HTMLElement);

/** Lets the animation frames after a close run, where the dialog library restores focus by itself. */
export const settled = () =>
  act(async () => {
    for (let i = 0; i < 5; i += 1) {
      await new Promise((resolve) => requestAnimationFrame(resolve));
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
  });

/** A copy of the fixture slice with scene `scene` changed at `path` (`undefined` deletes the member). */
export function change(scene: number, path: (string | number)[], value: Json | undefined): unknown {
  const copy = structuredClone(fixture.slice) as { scenes: Json[] };
  let at: Json = copy.scenes[scene] ?? null;
  for (const step of path.slice(0, -1)) at = (at as Members)[step] ?? null;
  const last = path[path.length - 1] ?? "";
  if (value === undefined) Reflect.deleteProperty(at as Members, last);
  else (at as Members)[last] = value;
  return copy;
}

/** A copy of the fixture whose "main" scene (index 0) is changed by `edit`. */
export function withMain(edit: (scene: Scene) => void): unknown {
  const copy = structuredClone(fixture.slice);
  const main = copy.scenes[0];
  if (main === undefined) throw new Error("the fixture has a first scene");
  edit(main);
  return copy;
}

// Every page test starts from its own hash and leaves none behind.
afterEach(() => {
  window.location.hash = "";
});
