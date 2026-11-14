// The reader's rules for Topics, the digest form and AI and cost. Refusals follow with the page.
import fixture from "../../../fixtures/signal.json";
import { readSlice } from "./slice";

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
});
