// A channel topic whose id is an Object.prototype name must not pass a lookup by inheritance:
// the reader refuses it when no order is delivered, and the pages never read an inherited value.
import { render, screen } from "@testing-library/react";
import fixture from "../../../fixtures/signal.json";
import { App } from "../../App";
import type { LoadResult } from "../../data";
import { readSlice } from "./slice";

type Scene = {
  snapshot: {
    channels: { topics: { id: string }[] };
    feed: { topics: Record<string, unknown> };
  };
};

/** The fixture with the "shipping" channel topic renamed to `id`, with or without its order. */
function renamed(id: string, keepOrder = false): unknown {
  const copy = structuredClone(fixture.slice) as unknown as { scenes: Scene[] };
  for (const { snapshot } of copy.scenes) {
    const topic = snapshot.channels.topics.find((t) => t.id === "shipping");
    if (topic !== undefined) topic.id = id;
    const orders = Object.entries(snapshot.feed.topics);
    // Object.fromEntries defines "__proto__" as an own key, as JSON.parse does.
    snapshot.feed.topics = Object.fromEntries(
      keepOrder
        ? orders.map(([key, order]) => [key === "shipping" ? id : key, order])
        : orders.filter(([key]) => key !== "shipping"),
    );
  }
  return copy;
}

describe("prototype-named topic ids", () => {
  afterEach(() => {
    window.location.hash = "";
  });
  for (const id of ["constructor", "toString", "__proto__"]) {
    it(`refuses channel topic "${id}" with no order`, () => {
      expect(readSlice(renamed(id))).toEqual({
        kind: "invalid",
        reason: `scenes[0].snapshot.feed.topics.${id}: expected an order for this channel topic`,
      });
    });
    it(`does not crash the topic page for "${id}"`, () => {
      const ok: LoadResult = {
        kind: "ok",
        data: { schema: "credit-os-data/1", issuers: [], signal: renamed(id) },
      };
      window.location.hash = `#/signal/main/topic/${id}`;
      expect(() => render(<App result={ok} />)).not.toThrow();
      expect(
        screen.getByText(/could not be read|No Signal data|No such topic/),
      ).toBeInTheDocument();
    });
    it(`reads the order delivered for topic "${id}" and its own follow state`, () => {
      const slice = renamed(id, true);
      expect(readSlice(slice).kind).toBe("ok");
      const ok: LoadResult = {
        kind: "ok",
        data: { schema: "credit-os-data/1", issuers: [], signal: slice },
      };
      window.location.hash = `#/signal/main/topic/${id}`;
      render(<App result={ok} />);
      expect(screen.getByRole("heading", { level: 2, name: "Shipping" })).toBeInTheDocument();
      // Shipping is followed in the fixture; Telecoms is not. Neither reads an inherited value.
      expect(screen.getByRole("button", { name: "Unfollow Shipping" })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
      expect(screen.getByRole("button", { name: "Follow Telecoms" })).toHaveAttribute(
        "aria-pressed",
        "false",
      );
    });
  }
});
