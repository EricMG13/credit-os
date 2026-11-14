// Unknown groups and digests, the unknown-scene link, and the rating-move list's position key.
import { render, screen } from "@testing-library/react";
import fixture from "../../../fixtures/signal.json";
import { App } from "../../App";
import type { LoadResult } from "../../data";

function show(hash: string, slice: unknown = fixture.slice) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], signal: slice },
  };
  return render(<App result={result} />);
}

const h1s = () => screen.getAllByRole("heading", { level: 1 }).map((h) => h.textContent);

describe("Signal states", () => {
  afterEach(() => {
    window.location.hash = "";
    vi.restoreAllMocks();
  });

  it.each([
    ["an unknown group", "/signal/main/group/nowhere", "No such group"],
    [
      "an unknown group on the thread route",
      "/signal/main/group/nowhere/thread/t",
      "No such group",
    ],
    ["an unknown digest", "/signal/main/digest/nowhere", "No such digest"],
  ])("draws %s as the one h1", (_name, hash, title) => {
    show(hash);
    expect(h1s()).toEqual([title]);
  });

  it("links an unknown scene back to the first scene's For you, not to itself", () => {
    const copy = structuredClone(fixture.slice);
    copy.scenes.reverse();
    expect(copy.scenes[0]?.id).not.toBe("main");
    show("/signal/nowhere/feed/for-you", copy);
    const first = copy.scenes[0]?.id ?? "";
    expect(screen.getByRole("link", { name: "Back to the sample scenes" })).toHaveAttribute(
      "href",
      `#/signal/${first}/feed/for-you`,
    );
  });

  it("draws two identical rating moves without a duplicate-key warning", () => {
    const copy = structuredClone(fixture.slice);
    const story = copy.scenes[0]?.snapshot.feed.stories[0];
    if (story === undefined) throw new Error("the fixture's main scene has a story");
    const move = { from: "BB-", to: "B+", word: "Downgrade, one notch" };
    story.ratingMoves = [move, { ...move }];
    const errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
    show("/signal/main/feed/for-you", copy);
    expect(screen.getAllByText("Downgrade, one notch")).toHaveLength(2 + 1);
    expect(errors.mock.calls.flat().join(" ")).not.toMatch(/same key|unique "key"/);
  });
});
