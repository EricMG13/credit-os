// Whole-branch finding M2: a pressed Save is kept per story id above the list, so the feed's own
// filters (which unmount a card) and a move between pages of one scene do not forget it. In memory
// only; the Saved badge and the Saved view are the slice's delivered sample values and do not change.
import { fireEvent, render, screen, within } from "@testing-library/react";
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
const CORVANE = "Corvane Packaging to close two plants as volumes fall";
const HALVORSEN = "Northgate Ratings downgrades Halvorsen Marine to B+";

describe("Save is kept by story id", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("keeps a press through a search that hides the card and clears it", () => {
    show("/signal/main/feed/for-you");
    fireEvent.click(content().getByRole("button", { name: `Save: ${CORVANE}` }));
    const search = screen.getByRole("textbox", { name: "Search stories" });
    fireEvent.change(search, { target: { value: "Halvorsen" } });
    expect(content().queryByRole("button", { name: /^Saved?: Corvane/ })).toBeNull();
    fireEvent.change(search, { target: { value: "" } });
    expect(content().getByRole("button", { name: `Saved: ${CORVANE}` })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("keeps an unsave of a story the slice delivers saved, through the kind tabs", () => {
    show("/signal/main/feed/for-you");
    fireEvent.click(content().getByRole("button", { name: `Saved: ${HALVORSEN}` }));
    fireEvent.click(screen.getByRole("tab", { name: "Regulators" }));
    expect(content().queryByRole("button", { name: /^Saved?: Northgate/ })).toBeNull();
    fireEvent.click(screen.getByRole("tab", { name: "All" }));
    expect(content().getByRole("button", { name: `Save: ${HALVORSEN}` })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("shows the same choice on the group page and the feed of one scene", async () => {
    show("/signal/main/feed/for-you");
    fireEvent.click(content().getByRole("button", { name: `Save: ${CORVANE}` }));
    window.location.hash = "#/signal/main/group/leveraged-credit";
    await screen.findByRole("heading", { level: 1, name: "Leveraged credit" });
    expect(content().getByRole("button", { name: `Saved: ${CORVANE}` })).toBeInTheDocument();
    // And the other way: an unsave on the group page reaches the feed.
    fireEvent.click(content().getByRole("button", { name: `Saved: ${HALVORSEN}` }));
    window.location.hash = "#/signal/main/feed/for-you";
    await screen.findByRole("heading", { level: 1, name: "For you" });
    expect(content().getByRole("button", { name: `Save: ${HALVORSEN}` })).toBeInTheDocument();
  });

  it("does not carry a choice to another scene", async () => {
    show("/signal/main/feed/for-you");
    fireEvent.click(content().getByRole("button", { name: `Save: ${CORVANE}` }));
    window.location.hash = "#/signal/reader/feed/for-you";
    await screen.findByText("Reader");
    expect(content().getByRole("button", { name: `Save: ${CORVANE}` })).toBeInTheDocument();
  });
});
