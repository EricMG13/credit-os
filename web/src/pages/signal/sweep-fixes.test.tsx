// Page fixes the sweep confirmed (register rows S1, S5, S8). Each test is the sweep probe's case, with
// its expected values stated here: a channel link opens its page, a repeated sentence is a fresh node,
// two lines with one text draw without a duplicate key.
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import fixture from "../../../fixtures/signal.json";
import { App } from "../../App";
import type { LoadResult } from "../../data";
import { readSlice } from "./slice";

function show(hash: string, slice: unknown = fixture.slice) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], signal: slice },
  };
  return render(<App result={result} />);
}
const settled = () =>
  act(async () => {
    for (let i = 0; i < 5; i += 1) await new Promise((r) => requestAnimationFrame(r));
    await new Promise((r) => setTimeout(r, 50));
  });
const keyErrors = (spy: { mock: { calls: unknown[][] } }) =>
  spy.mock.calls.filter((call) => call.some((a) => String(a).includes("same key")));

afterEach(() => {
  window.location.hash = "";
  vi.restoreAllMocks();
});

describe("S1: a channel link encodes the id it carries", () => {
  /** The fixture with one id renamed wherever it stands (channel list, pages, settings, orders, refs): an exact quoted match. */
  const renamed = (from: string, to: string): unknown =>
    JSON.parse(JSON.stringify(fixture.slice).replaceAll(`"${from}"`, `"${to}"`));
  const CASES: [string, string, string, string][] = [
    ["shipping", "rates/fx", "Shipping", "#/signal/main/topic/rates%2Ffx"],
    ["shipping-desk", "desk/2", "Shipping desk", "#/signal/main/group/desk%2F2"],
    ["weekly-brief", "weekly/brief", "Weekly brief", "#/signal/main/digest/weekly%2Fbrief"],
  ];
  it.each(CASES)(
    "%s as %s: the link is encoded and opens its page",
    async (from, to, name, href) => {
      const slice = renamed(from, to);
      expect(readSlice(slice).kind).toBe("ok");
      show("/signal/main/feed/for-you", slice);
      const link = within(screen.getByRole("navigation", { name: "Signal" }))
        .getAllByRole("link")
        .find((a) => a.textContent.startsWith(name));
      expect(link).toHaveAttribute("href", href);
      window.location.hash = href;
      await waitFor(() => {
        expect(screen.getAllByRole("heading", { level: 1 }).map((h) => h.textContent)).toEqual([
          name,
        ]);
      });
      expect(screen.queryByText(/Page not found|No such|does not exist/)).toBeNull();
    },
  );
});

describe("S5: a repeated sentence is announced again", () => {
  it("a second 'Comment posted' in a thread is a fresh node in the same status region", () => {
    show("/signal/main/group/leveraged-credit/thread/corvane-thread");
    const panel = screen.getByRole("dialog", { name: "Thread" });
    const box = within(panel).getByRole("textbox", { name: "Write a comment" });
    const post = (text: string) => {
      fireEvent.change(box, { target: { value: text } });
      fireEvent.click(within(panel).getByRole("button", { name: "Send" }));
    };
    post("First note.");
    const status = within(panel).getByRole("status");
    expect(status).toHaveTextContent("Comment posted");
    const first = status.firstChild;
    post("Second note.");
    expect(within(panel).getByRole("status")).toBe(status);
    expect(status).toHaveTextContent("Comment posted");
    expect(status.firstChild).not.toBe(first);
    expect(status.querySelectorAll('[role="status"], [aria-live]')).toHaveLength(0);
  });

  it("setting the same name again is a fresh node in the same status region", async () => {
    show("/signal/main/feed/for-you");
    const rename = async () => {
      fireEvent.click(screen.getByRole("button", { name: /Mara L/ }));
      const dialog = await screen.findByRole("dialog", { name: "Your name" });
      fireEvent.click(within(dialog).getByRole("button", { name: "Continue" }));
      await waitFor(() => {
        expect(screen.queryByRole("dialog", { hidden: true })).toBeNull();
      });
      await settled();
    };
    await rename();
    const status = screen
      .getAllByRole("status")
      .find((s) => s.textContent === "Signed in as Mara L");
    if (status === undefined) throw new Error("no status says Signed in as Mara L");
    const first = status.firstChild;
    await rename();
    expect(status.isConnected).toBe(true);
    expect(status).toHaveTextContent("Signed in as Mara L");
    expect(status.firstChild).not.toBe(first);
  });
});

describe("S8: lines with one text are keyed by slot", () => {
  it("a failing source whose health note repeats its reason draws both lines, with no duplicate key", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const slice = structuredClone(fixture.slice);
    const failing = slice.scenes[0]?.snapshot.settings.sources.find((o) => o.health === "Failing");
    if (failing?.reason == null) throw new Error("main lists a failing source");
    Object.assign(failing, { healthNote: failing.reason });
    expect(readSlice(slice).kind).toBe("ok");
    show("/signal/main/settings/sources", slice);
    expect(screen.getAllByText(failing.reason)).toHaveLength(2);
    expect(keyErrors(spy)).toEqual([]);
  });

  it("an earlier issue whose summary repeats its nothing line draws both lines, with no duplicate key", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const slice = structuredClone(fixture.slice);
    const issue = slice.scenes[0]?.snapshot.digests.find((d) => d.id === "weekly-brief")?.issues[0];
    if (issue?.summary == null) throw new Error("main has a weekly brief issue with a summary");
    Object.assign(issue, { ai: false, points: [], nothing: issue.summary });
    expect(readSlice(slice).kind).toBe("ok");
    show("/signal/main/digest/weekly-brief", slice);
    expect(screen.getAllByText(issue.summary)).toHaveLength(2);
    expect(keyErrors(spy)).toEqual([]);
  });
});
