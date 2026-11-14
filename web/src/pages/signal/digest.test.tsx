// The digest page (mock digests frames 1, 3 and 4). Expected wording is the mock's, not the code's.
import { fireEvent, render, screen, within } from "@testing-library/react";
import fixture from "../../../fixtures/signal.json";
import { App } from "../../App";
import type { LoadResult } from "../../data";

type Scene = (typeof fixture.slice.scenes)[number];

function show(hash: string, slice: unknown = fixture.slice) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], signal: slice },
  };
  return render(<App result={result} />);
}

/** A copy of the fixture whose scene `id` is changed by `change`. */
function with_(id: string, change: (scene: Scene) => void): unknown {
  const copy = structuredClone(fixture.slice);
  const scene = copy.scenes.find((s) => s.id === id);
  if (scene === undefined) throw new Error(`the fixture has the scene ${id}`);
  change(scene);
  return copy;
}

/** The page itself, without the channel list beside it. */
/** The "main" scene with AI turned on (no digest paused; the rule ties the two) and Daily ratings changed by `change`. */
function running(change: (digest: Scene["snapshot"]["digests"][number]) => void): unknown {
  return with_("main", (scene) => {
    const { snapshot } = scene;
    const digest = snapshot.digests[1];
    if (digest === undefined) throw new Error("main has Daily ratings");
    Object.assign(snapshot.settings.ai, { state: "on", notice: null });
    for (const channel of snapshot.channels.digests) channel.paused = false;
    for (const one of snapshot.digests) {
      Object.assign(one, { paused: null });
      // A running digest's newest issue has points or a nothing-material sentence.
      for (const issue of one.issues.slice(0, 1)) {
        Object.assign(issue, { ai: false, summary: null, nothing: "Nothing material to report." });
      }
    }
    change(digest);
  });
}

const page = () => within(document.getElementById("signal-content") as HTMLElement);
const headings = (level: number) =>
  page()
    .getAllByRole("heading", { level })
    .map((h) => h.textContent);

const WEEKLY = "Leveraged credit: the week to 13 November";
const EARLIER = "Leveraged credit: the week to 6 November";
const NOTHING_TITLE = "Rating actions: 13 November";
const NOTHING_SENTENCE =
  "No rating action reached this digest's sources on 13 November. The next digest is due on Mon 16 Nov.";
const PAUSED =
  "No new digest is written while AI is off or at its cap. Earlier digests stay readable.";

afterEach(() => {
  window.location.hash = "";
});

describe("a digest with its newest issue (frame 1)", () => {
  it("takes the issue's title as the h1, the points as h2 and Earlier digests as an h2 with an h3 row", () => {
    show("/signal/ai-on/digest/weekly-brief");
    expect(headings(1)).toEqual([WEEKLY]);
    expect(headings(2)).toEqual([
      "Packaging issuers are cutting capacity, not prices",
      "Two telecoms disposals are now in in-depth review",
      "Shipping downgrades cluster around 2027 maturities",
      "Loan extensions are clearing at a higher margin",
      "A port operator is preparing a first bond",
      "Earlier digests",
    ]);
    expect(headings(3)).toEqual([EARLIER]);
  });

  it("draws the meta line (Digest, AI, name, date) then the delivered summary line", () => {
    show("/signal/ai-on/digest/weekly-brief");
    const h1 = page().getByRole("heading", { level: 1 });
    const meta = h1.previousElementSibling as HTMLElement;
    expect(within(meta).getByText("Digest")).toBeInTheDocument();
    expect(within(meta).getByText("AI")).toBeInTheDocument();
    expect(meta.textContent).toBe("DigestAIWeekly briefFri 13 Nov 2026");
    expect(h1.nextElementSibling?.textContent).toBe(
      "Covers 9 to 13 Nov 2026. Written by a model from 41 stories in Leveraged credit, Shipping and Packaging.",
    );
  });

  it("draws the delivered number, lead and body of each point", () => {
    show("/signal/ai-on/digest/weekly-brief");
    const points = page()
      .getAllByRole("listitem")
      .filter((li) => /^\d/.test(li.textContent));
    expect(points.map((li) => li.textContent.slice(0, 1))).toEqual(["1", "2", "3", "4", "5"]);
    expect(
      within(points[3] as HTMLElement).getByText(
        "Brightwell Foods extended by three years for 50 basis points more. It is the fourth extension this quarter priced that way.",
      ),
    ).toBeInTheDocument();
  });

  it("takes a point's number from the data, not from its position", () => {
    show(
      "/signal/ai-on/digest/weekly-brief",
      with_("ai-on", (scene) => {
        const first = scene.snapshot.digests[0]?.issues[0]?.points[0];
        if (first === undefined) throw new Error("the fixture has a first point");
        first.number = "A";
      }),
    );
    expect(page().getAllByRole("listitem")[0]?.textContent).toMatch(/^APackaging issuers/);
  });

  it("draws the delivered stories line above each point's stories, and leaves it out when null", () => {
    show("/signal/ai-on/digest/weekly-brief");
    expect(page().getByText("3 stories behind this point")).toBeInTheDocument();
    expect(page().getByText("1 story behind this point")).toBeInTheDocument();
    expect(page().getAllByText(/stories behind this point/)).toHaveLength(4);
  });

  it("leaves the stories line out of a point whose line is null", () => {
    show(
      "/signal/ai-on/digest/weekly-brief",
      with_("ai-on", (scene) => {
        const first = scene.snapshot.digests[0]?.issues[0]?.points[0];
        if (first === undefined) throw new Error("the fixture has a first point");
        Object.assign(first, { storiesLine: null });
      }),
    );
    expect(page().queryByText("3 stories behind this point")).not.toBeInTheDocument();
  });

  it("links each story to its source in a new tab, named as the story card names it", () => {
    show("/signal/ai-on/digest/weekly-brief");
    const point = within(
      screen.getByRole("list", {
        name: "Stories behind: Packaging issuers are cutting capacity, not prices",
      }),
    );
    const link = point.getByRole("link", {
      name: "Open source: Corvane Packaging to close two plants as volumes fall (opens in a new tab)",
    });
    expect(link).toHaveAttribute("href", "https://example.com/harbour-wire/corvane-plants");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(point.getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "Corvane Packaging to close two plants as volumes fall, Harbour Wire, 13 Nov",
      "Delmere Board mothballs its northern mill, Credit Ledger Daily, 11 Nov",
      "Packaging volumes fall for a third quarter, The Meridian Post, 10 Nov",
    ]);
  });

  it("draws a story with no link as plain text ending (no link), as frame 1 does", () => {
    show("/signal/ai-on/digest/weekly-brief");
    const point = within(
      screen.getByRole("list", {
        name: "Stories behind: A port operator is preparing a first bond",
      }),
    );
    const plain = "Notice of initial review: Oakhaven Lines and Pellant Terminals";
    expect(point.getByText(`${plain}, Regulatory Gazette, 13 Nov (no link)`)).toBeInTheDocument();
    expect(point.queryByRole("link", { name: new RegExp(plain) })).not.toBeInTheDocument();
  });

  it.each(["ftp://example.com/a", "javascript:alert(1)"])(
    "draws the address %s as plain text, not a link",
    (url) => {
      show(
        "/signal/ai-on/digest/weekly-brief",
        with_("ai-on", (scene) => {
          const story = scene.snapshot.digests[0]?.issues[0]?.points[3]?.stories[0];
          if (story === undefined) throw new Error("the fixture has the point's story");
          story.url = url;
        }),
      );
      const list = within(
        screen.getByRole("list", {
          name: "Stories behind: Loan extensions are clearing at a higher margin",
        }),
      );
      expect(list.queryByRole("link")).not.toBeInTheDocument();
      expect(
        list.getByText(
          "Brightwell Foods extends its term loan by three years, Credit Ledger Daily, 12 Nov (no link)",
        ),
      ).toBeInTheDocument();
    },
  );

  it("leaves a missing time out of the story line", () => {
    show(
      "/signal/ai-on/digest/weekly-brief",
      with_("ai-on", (scene) => {
        const story = scene.snapshot.digests[0]?.issues[0]?.points[3]?.stories[0];
        if (story === undefined) throw new Error("the fixture has the point's story");
        Object.assign(story, { time: null });
      }),
    );
    const list = screen.getByRole("list", {
      name: "Stories behind: Loan extensions are clearing at a higher margin",
    });
    expect(
      within(list)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["Brightwell Foods extends its term loan by three years, Credit Ledger Daily"]);
  });

  it("keeps the mock's 820px column", () => {
    show("/signal/ai-on/digest/weekly-brief");
    expect(page().getByRole("heading", { level: 1 }).parentElement).toHaveClass("max-w-[820px]");
  });
});

describe("Earlier digests as rows (frame 4)", () => {
  it("draws an earlier issue as a row: tile, labels, date, h3 title with the issue's id, summary, no link and no points", () => {
    show("/signal/ai-on/digest/weekly-brief");
    const title = document.querySelector('[data-issue="week-6-nov"]');
    expect(title?.tagName).toBe("H3");
    expect(title?.textContent).toBe(EARLIER);
    const row = within(title?.closest("li") as HTMLElement);
    expect(row.getByText("WB")).toBeInTheDocument();
    expect(row.getByText("Digest")).toBeInTheDocument();
    expect(row.getByText("AI")).toBeInTheDocument();
    expect(row.getByText("Fri 6 Nov")).toBeInTheDocument();
    expect(row.getByText("5 points from 36 stories")).toBeInTheDocument();
    expect(row.queryByRole("link")).not.toBeInTheDocument();
    expect(row.queryByRole("list")).not.toBeInTheDocument();
  });

  it("holds the issue a feed card names, as a row", () => {
    show("/signal/ai-on/digest/daily-ratings");
    expect(document.querySelector('[data-issue="12-nov"]')?.textContent).toBe(
      "Rating actions: 12 November",
    );
  });
});

describe("a digest with nothing material (frame 3)", () => {
  it("draws the meta line without AI, the title as the h1 and the kit empty state", () => {
    show("/signal/ai-on/digest/daily-ratings");
    expect(headings(1)).toEqual([NOTHING_TITLE]);
    const h1 = page().getByRole("heading", { level: 1 });
    expect((h1.previousElementSibling as HTMLElement).textContent).toBe(
      "DigestDaily ratingsFri 13 Nov 2026",
    );
    expect(headings(2)).toEqual(["Nothing material to report", "Earlier digests"]);
    expect(page().getByText(NOTHING_SENTENCE)).toBeInTheDocument();
    expect(page().queryByText("AI")).toBeInTheDocument(); // the earlier row's own label
    expect(h1.previousElementSibling).not.toHaveTextContent("AI");
  });

  it("draws no numbered list for it", () => {
    show("/signal/ai-on/digest/daily-ratings");
    expect(page().queryByRole("list", { name: /Stories behind/ })).not.toBeInTheDocument();
    expect(
      page()
        .queryAllByRole("listitem")
        .filter((li) => /^\d/.test(li.textContent)),
    ).toEqual([]);
  });

  it("moves focus to the Earlier digests heading from See earlier digests, leaving the hash alone", () => {
    show("/signal/ai-on/digest/daily-ratings");
    const hash = window.location.hash;
    fireEvent.click(page().getByRole("button", { name: "See earlier digests" }));
    expect(document.activeElement).toBe(
      page().getByRole("heading", { level: 2, name: "Earlier digests" }),
    );
    expect(window.location.hash).toBe(hash);
  });

  it("offers See earlier digests only when earlier issues exist", () => {
    show(
      "/signal/main/digest/daily-ratings",
      running((digest) => {
        digest.issues = [
          {
            id: "11-nov",
            title: NOTHING_TITLE,
            date: "Fri 13 Nov 2026",
            ai: false,
            summary: null,
            nothing: NOTHING_SENTENCE,
            points: [],
          },
        ];
      }),
    );
    expect(headings(1)).toEqual([NOTHING_TITLE]);
    expect(page().getByText(NOTHING_SENTENCE)).toBeInTheDocument();
    expect(page().queryByRole("button", { name: /See earlier digests/ })).not.toBeInTheDocument();
    expect(page().queryByRole("heading", { name: "Earlier digests" })).not.toBeInTheDocument();
  });
});

describe("the channel list beside a digest", () => {
  it("marks the digest's own channel item as the current page", () => {
    show("/signal/ai-on/digest/daily-ratings");
    const nav = within(screen.getByRole("navigation", { name: "Signal" }));
    expect(nav.getByRole("link", { name: /^Daily ratings/ })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(nav.getByRole("link", { name: /^Weekly brief/ })).not.toHaveAttribute("aria-current");
  });
});

describe("a paused digest (frame 4)", () => {
  it("takes its name as the h1 with a Paused badge, the alert and the AI and cost link", () => {
    show("/signal/main/digest/weekly-brief");
    expect(headings(1)).toEqual(["Weekly brief"]);
    const alert = page().getByRole("status");
    expect(alert).toHaveTextContent(PAUSED);
    expect(alert).toHaveTextContent("Info");
    expect(within(alert).getByRole("link", { name: "Open AI and cost" })).toHaveAttribute(
      "href",
      "#/signal/main/settings/ai",
    );
    expect(page().getByText("Paused")).toBeInTheDocument();
  });

  it("offers a writer the AI and cost link and a reader none", () => {
    show("/signal/reader/digest/weekly-brief");
    expect(page().getByText("AI is off.")).toBeInTheDocument();
    expect(page().queryByRole("link", { name: /AI and cost/ })).not.toBeInTheDocument();
  });

  it("draws every issue as a row under Earlier digests, with its own summary and no points", () => {
    show("/signal/main/digest/weekly-brief");
    expect(headings(2)).toEqual(["Earlier digests"]);
    expect(headings(3)).toEqual([WEEKLY]);
    expect(page().getByText("5 points from 41 stories")).toBeInTheDocument();
    expect(page().queryByRole("list", { name: /Stories behind/ })).not.toBeInTheDocument();
  });

  it("draws no Paused badge and no alert on a digest that is running", () => {
    show("/signal/ai-on/digest/weekly-brief");
    expect(page().queryByText("Paused")).not.toBeInTheDocument();
    expect(page().queryByRole("status")).not.toBeInTheDocument();
  });
});

describe("a digest the page cannot show", () => {
  it("says an unknown digest is not in this sample, as the one h1", () => {
    show("/signal/main/digest/nowhere");
    expect(headings(1)).toEqual(["No such digest in this sample"]);
  });

  it("looks the digest up by value: an id such as constructor is no special case", () => {
    show("/signal/main/digest/constructor");
    expect(headings(1)).toEqual(["No such digest in this sample"]);
  });

  it("says a digest with no issue has no digest yet, under its own name, with the pause kept", () => {
    show("/signal/main/digest/daily-ratings");
    expect(headings(1)).toEqual(["Daily ratings"]);
    expect(headings(2)).toEqual(["No digest yet"]);
    expect(page().getByRole("status")).toHaveTextContent(PAUSED);
  });

  it("says a running digest with no issue has no digest yet, under its own name", () => {
    show(
      "/signal/main/digest/daily-ratings",
      running((digest) => {
        digest.issues = [];
      }),
    );
    expect(headings(1)).toEqual(["Daily ratings"]);
    expect(headings(2)).toEqual(["No digest yet"]);
    expect(page().queryByRole("status")).not.toBeInTheDocument();
  });
});
