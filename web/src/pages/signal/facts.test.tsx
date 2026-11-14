// One fact, one value (register rows S3, S4, S6): the same fact drawn on two Signal surfaces agrees.
// Expected values are mock frame 4's keywords, the thread panel's own count, and the empty Saved view.
import { render, screen, waitFor, within } from "@testing-library/react";
import fixture from "../../../fixtures/signal.json";
import { App } from "../../App";
import type { LoadResult } from "../../data";

function show(hash: string) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], signal: fixture.slice },
  };
  return render(<App result={result} />);
}
const content = () => within(document.getElementById("signal-content") as HTMLElement);
const nav = () => within(screen.getByRole("navigation", { name: "Signal" }));
const CORVANE = "Corvane Packaging to close two plants as volumes fall";
const TELECOMS = ["towers", "fibre", "spectrum", "Tessaly"];
const words = (list: HTMLElement | null) =>
  [...(list?.querySelectorAll("li") ?? [])].map((li) => li.textContent);

describe("one fact, one value", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("S6: the feed's Comment count is the count of the thread it opens", async () => {
    show("/signal/main/feed/for-you");
    const comment = content().getByRole("link", { name: `Comment 4: ${CORVANE}` });
    window.location.hash = comment.getAttribute("href") ?? "";
    const panel = await screen.findByRole("dialog", { name: "Thread" });
    expect(within(panel).getByText("Leveraged credit, 4 comments")).toBeInTheDocument();
  });

  it("S6: a story with no thread draws no count beside Comment", () => {
    show("/signal/ai-on/feed/for-you");
    expect(content().getByRole("button", { name: `Comment: ${CORVANE}` })).toHaveTextContent(
      /^Comment$/,
    );
  });

  it("S4: a reader's Saved badge says 0 beside the empty Saved page", async () => {
    show("/signal/reader/feed/saved");
    await screen.findByRole("heading", { level: 1, name: "Saved" });
    expect(nav().getByRole("link", { name: /^Saved/ })).toHaveTextContent(/^Saved\s*0$/);
    expect(content().getByText("Stories you save appear here")).toBeInTheDocument();
  });

  it("S4: a loading feed draws no Saved badge", () => {
    show("/signal/loading/feed/for-you");
    expect(nav().getByRole("link", { name: /^Saved/ })).toHaveTextContent(/^Saved\s*$/);
  });

  it.each(["main", "reader", "ai-on"])(
    "S3: a topic's keywords are the same on its page and in Settings (%s)",
    async (scene) => {
      show(`/signal/${scene}/topic/telecoms`);
      await screen.findByRole("heading", { level: 1, name: "Telecoms" });
      expect(words(content().getByRole("list", { name: "Topic keywords" }))).toEqual(TELECOMS);
      window.location.hash = `#/signal/${scene}/settings/topics`;
      const listed = await screen.findByRole("list", { name: "Keywords: Telecoms" });
      await waitFor(() => {
        expect(words(listed)).toEqual(TELECOMS);
      });
    },
  );

  it("S3: a topic with no keywords draws no keyword row on its page and says so in Settings", async () => {
    show("/signal/main/topic/rating-actions");
    await screen.findByRole("heading", { level: 1, name: "Rating actions" });
    expect(content().queryByRole("list", { name: "Topic keywords" })).toBeNull();
    window.location.hash = "#/signal/main/settings/topics";
    expect(await screen.findByText("No keywords: every story of this kind")).toBeInTheDocument();
  });
});
