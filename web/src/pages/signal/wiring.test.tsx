// A topic order is looked up by its own key: a channel topic named like an Object.prototype member
// whose order is missing must raise the wiring-fault error, not read an inherited value.
import { render } from "@testing-library/react";
import fixture from "../../../fixtures/signal.json";
import { App } from "../../App";
import type { LoadResult } from "../../data";
import type * as SliceModule from "./slice";
import { readSlice, type SignalSlice } from "./slice";

const actual = await vi.importActual<typeof SliceModule>("./slice");
vi.mock("./slice", async (importOriginal) => {
  const real = await importOriginal<typeof SliceModule>();
  return { ...real, readSlice: vi.fn(real.readSlice) };
});

/** The fixture's main scene with channel topic "constructor" and an ordinary-object order list lacking it. */
function withoutOrder(): SignalSlice {
  const read = actual.readSlice(fixture.slice);
  if (read.kind !== "ok") throw new Error("the fixture reads");
  const copy = structuredClone(read.data);
  const { feed, channels } = copy.scenes[0].snapshot;
  channels.topics[0] = {
    id: "constructor",
    name: "Constructor",
    count: null,
    followed: false,
    keywords: [],
  };
  feed.topics = {};
  return copy;
}

describe("the topic page's order lookup", () => {
  afterEach(() => {
    window.location.hash = "";
    vi.spyOn(console, "error").mockRestore();
  });

  it("throws the wiring-fault error when a topic has no order of its own", () => {
    vi.mocked(readSlice).mockReturnValue({ kind: "ok", data: withoutOrder() });
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const ok: LoadResult = {
      kind: "ok",
      data: { schema: "credit-os-data/1", issuers: [], signal: fixture.slice },
    };
    window.location.hash = "#/signal/main/topic/constructor";
    expect(() => render(<App result={ok} />)).toThrow(
      'the slice reader let through topic "constructor" with no order',
    );
  });
});
