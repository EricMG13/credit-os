import { fireEvent, render, screen, within } from "@testing-library/react";
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

/** A copy of the fixture slice with the first story of scene `main` changed. */
function withFirstStory(change: Record<string, unknown>): unknown {
  const copy = structuredClone(fixture.slice);
  const first = copy.scenes[0]?.snapshot.feed.stories[0];
  if (first === undefined) throw new Error("the fixture's main scene has a story");
  Object.assign(first, change);
  return copy;
}

/** The story whose headline is the given text (mock frames 1, 10 and 11 give the wording). */
function story(headline: string) {
  const heading = screen.getByRole("heading", { level: 3, name: headline });
  const article = heading.closest("article");
  if (article === null) throw new Error("a story headline sits in an article");
  return within(article);
}

const CORVANE = "Corvane Packaging to close two plants as volumes fall";
const BRIGHTWELL = "Brightwell Foods extends its term loan by three years";
const OAKHAVEN = "Notice of initial review: Oakhaven Lines and Pellant Terminals";
const TESSALY = "Competition authority opens in-depth review of Tessaly Telecom's tower sale";
const HALVORSEN = "Northgate Ratings downgrades Halvorsen Marine to B+";
const PELLANT = "Pellant Terminals plans first bond issue";

describe("the feed list and the story card", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("draws each story as an article with its headline as an h3, in the view's order", () => {
    show("/signal/main/feed/for-you");
    expect(screen.getAllByRole("article")).toHaveLength(4);
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      CORVANE,
      TESSALY,
      HALVORSEN,
      BRIGHTWELL,
    ]);
    expect(screen.getByRole("heading", { level: 2, name: "For you" })).toBeInTheDocument();
  });

  it("draws kind, publication, time, summary, tags and the monogram tile", () => {
    show("/signal/main/feed/for-you");
    const card = story(CORVANE);
    expect(card.getByText("News")).toBeInTheDocument();
    expect(card.getByText("Harbour Wire")).toBeInTheDocument();
    expect(card.getByText("2 h ago")).toBeInTheDocument();
    expect(
      card.getByText(/^Corvane will shut two of its nine plants by March/),
    ).toBeInTheDocument();
    expect(card.getByText("Packaging")).toBeInTheDocument();
    expect(card.getByText("Restructuring")).toBeInTheDocument();
    expect(card.getByText("HW")).toBeInTheDocument();
  });

  it("links the headline and Open source to the story, in a new tab", () => {
    show("/signal/main/feed/for-you");
    const card = story(CORVANE);
    for (const link of [
      card.getByRole("link", { name: CORVANE }),
      card.getByRole("link", { name: `Open source: ${CORVANE} (opens in a new tab)` }),
    ]) {
      expect(link).toHaveAttribute("href", "https://example.com/corvane");
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
    }
  });

  it("with no link draws a plain headline and no Open source", () => {
    show("/signal/main/feed/latest");
    const card = story(OAKHAVEN);
    expect(card.queryByRole("link")).not.toBeInTheDocument();
    expect(card.queryByText("Open source")).not.toBeInTheDocument();
    expect(card.getByText("40 min ago")).toBeInTheDocument();
    expect(story(PELLANT).getByRole("link", { name: /^Open source: Pellant/ })).toBeInTheDocument();
  });

  it("with no time leaves the time out, and writes no n.a. on a story", () => {
    show("/signal/main/feed/latest");
    const card = story(PELLANT);
    expect(card.getByText("Credit Ledger Daily")).toBeInTheDocument();
    expect(card.queryByText(/ago|Yesterday|n\.a\./)).not.toBeInTheDocument();
  });

  it("with AI off draws no AI line and no strength", () => {
    show("/signal/main/feed/for-you");
    expect(screen.queryByText("AI")).not.toBeInTheDocument();
    expect(screen.queryByRole("img", { name: /signal$/ })).not.toBeInTheDocument();
    expect(screen.queryByText("Shared to Leveraged credit by Tobias O")).not.toBeInTheDocument();
  });

  it("with AI on draws the AI label with its line, the strength and its word", () => {
    show("/signal/ai-on/feed/for-you");
    const card = story(CORVANE);
    expect(card.getByText("AI")).toBeInTheDocument();
    expect(
      card.getByText("The charge lands in the quarter its leverage covenant steps down."),
    ).toBeInTheDocument();
    const strong = card.getByRole("img", { name: "Strong signal" });
    expect(strong.querySelectorAll("svg.fill-current")).toHaveLength(3);
    expect(strong.querySelectorAll("svg")).toHaveLength(3);
    const light = story(BRIGHTWELL).getByRole("img", { name: "Light signal" });
    expect(light.querySelectorAll("svg.fill-current")).toHaveLength(1);
  });

  it("draws the delivered also-in label with its monograms, and the shared-by line", () => {
    show("/signal/ai-on/feed/for-you");
    const card = story(CORVANE);
    expect(card.getByText("Also in 4 other sources")).toBeInTheDocument();
    for (const mark of ["CL", "MP", "RG", "+1"]) expect(card.getByText(mark)).toBeInTheDocument();
    expect(card.getByText("Shared to Leveraged credit by Tobias O")).toBeInTheDocument();
    expect(card.getByText("TO")).toBeInTheDocument();
    expect(story(BRIGHTWELL).queryByText(/Also in|Shared to/)).not.toBeInTheDocument();
  });

  it("gives a writer Comment (with its count), Share to group and Save", () => {
    show("/signal/main/feed/for-you");
    const card = story(CORVANE);
    const comment = card.getByRole("button", { name: `Comment 3: ${CORVANE}` });
    expect(within(comment).getByText("3")).toBeInTheDocument();
    expect(card.getByRole("button", { name: `Share to group: ${CORVANE}` })).toBeInTheDocument();
    expect(card.getByRole("button", { name: `Save: ${CORVANE}` })).toBeInTheDocument();
    const none = story(BRIGHTWELL).getByRole("button", { name: `Comment: ${BRIGHTWELL}` });
    expect(none).toHaveTextContent(/^Comment$/);
  });

  it("gives a reader Save and no Comment or Share to group", () => {
    show("/signal/reader/feed/for-you");
    expect(screen.getAllByRole("button", { name: /^Save: / })).toHaveLength(2);
    expect(screen.queryByRole("button", { name: /Comment/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Share to group/ })).not.toBeInTheDocument();
  });

  it("toggles Save in memory", () => {
    show("/signal/main/feed/for-you");
    const save = story(CORVANE).getByRole("button", { name: `Save: ${CORVANE}` });
    expect(save).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(save);
    const saved = story(CORVANE).getByRole("button", { name: `Saved: ${CORVANE}` });
    expect(saved).toHaveAttribute("aria-pressed", "true");
    expect(story(BRIGHTWELL).getByRole("button", { name: `Save: ${BRIGHTWELL}` })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    fireEvent.click(saved);
    expect(story(CORVANE).getByRole("button", { name: `Save: ${CORVANE}` })).toBeInTheDocument();
  });

  it("lets a long headline and summary wrap: nothing is truncated", () => {
    show("/signal/main/feed/for-you");
    const card = story(CORVANE);
    const nodes = [
      screen.getByRole("heading", { level: 3, name: CORVANE }),
      card.getByText(/^Corvane will shut two/),
    ];
    for (const node of nodes) {
      for (const el of [node, ...Array.from(node.querySelectorAll("*"))]) {
        expect(el.className).not.toMatch(/truncate|line-clamp|text-ellipsis|whitespace-nowrap/);
      }
    }
  });

  it("draws nothing under the title for a view with no stories", () => {
    show("/signal/reader/feed/saved");
    expect(screen.getByRole("heading", { level: 2, name: "Saved" })).toBeInTheDocument();
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
  });

  it("keeps the visible Save text short while the name carries the headline", () => {
    show("/signal/main/feed/for-you");
    expect(story(CORVANE).getByRole("button", { name: `Save: ${CORVANE}` })).toHaveTextContent(
      /^Save$/,
    );
  });

  it("starts Save from the slice's saved true, as Saved and pressed", () => {
    show("/signal/main/feed/for-you", withFirstStory({ saved: true }));
    const saved = story(CORVANE).getByRole("button", { name: `Saved: ${CORVANE}` });
    expect(saved).toHaveAttribute("aria-pressed", "true");
    expect(saved).toHaveTextContent(/^Saved$/);
    fireEvent.click(saved);
    expect(story(CORVANE).getByRole("button", { name: `Save: ${CORVANE}` })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("draws no tag list for a story with no tags", () => {
    show("/signal/main/feed/latest");
    expect(story(PELLANT).queryByRole("list")).not.toBeInTheDocument();
  });

  it("draws the tag list for a story with tags", () => {
    show("/signal/main/feed/for-you");
    expect(story(CORVANE).getByRole("list")).toBeInTheDocument();
  });

  it.each(["ftp://example.com/corvane", "file:///etc/hosts", "javascript:alert(1)"])(
    "draws the url %s as plain text with no link and no Open source",
    (url) => {
      show("/signal/main/feed/for-you", withFirstStory({ url }));
      const card = story(CORVANE);
      expect(card.queryByRole("link")).not.toBeInTheDocument();
      expect(card.queryByText("Open source")).not.toBeInTheDocument();
    },
  );

  it("draws an http address as a link too", () => {
    show("/signal/main/feed/for-you", withFirstStory({ url: "http://example.com/corvane" }));
    expect(story(CORVANE).getByRole("link", { name: CORVANE })).toHaveAttribute(
      "href",
      "http://example.com/corvane",
    );
  });

  it("draws the headline link in the primary text colour, not the link colour", () => {
    show("/signal/main/feed/for-you");
    const link = story(CORVANE).getByRole("link", { name: CORVANE });
    expect(link.className).toContain("text-text-primary");
    expect(link.className).not.toContain("text-text-link");
  });
});
