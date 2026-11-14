// The regulatory case's stage tracker, the rating move and the digest card (mock feed frames 1, 3
// and 4, digests frame 2). Expected wording is the mock's, not read from the code.
import { render, screen, within } from "@testing-library/react";
import fixture from "../../../fixtures/signal.json";
import { App } from "../../App";
import { NumberedPanel } from "./parts/NumberedPanel";
import { StageProgress } from "./parts/StageProgress";
import { Tags } from "./parts/Tags";
import type { LoadResult } from "../../data";

function show(hash: string) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], signal: fixture.slice },
  };
  return render(<App result={result} />);
}

function card(headline: string) {
  const heading = screen.getByRole("heading", { level: 2, name: headline });
  const article = heading.closest("article");
  if (article === null) throw new Error("a headline sits in an article");
  return within(article);
}

const TESSALY = "Competition authority opens in-depth review of Tessaly Telecom's tower sale";
const CLEARANCE = "Authority clears Brightwell Foods' dairy purchase with conditions";
const OAKHAVEN = "Notice of initial review: Oakhaven Lines and Pellant Terminals";
const HALVORSEN = "Northgate Ratings downgrades Halvorsen Marine to B+";
const AFFIRM = "Northgate Ratings affirms Oakhaven Lines at BB, outlook to positive";
const WEEKLY = "Leveraged credit: the week to 13 November";
const DAILY = "Rating actions: 12 November";
const NOTHING = "Rating actions: 11 November";
const STAGES = ["Opened", "Initial review", "In-depth review", "Decision"];

afterEach(() => {
  window.location.hash = "";
});

describe("the stage tracker", () => {
  it("draws the current stage, the delivered label, the track and the four stage names", () => {
    show("/signal/ai-on/feed/for-you");
    const tessaly = card(TESSALY);
    const bar = tessaly.getByRole("progressbar", { name: "Case stage" });
    expect(bar).toHaveAttribute("aria-valuetext", "Stage 3 of 4: In-depth review");
    expect(bar).toHaveAttribute("aria-valuenow", "0.75");
    expect(bar.firstElementChild).toHaveStyle({ width: "75%" });
    expect(tessaly.getByText("Stage 3 of 4")).toBeInTheDocument();
    const names = tessaly.getAllByRole("listitem").filter((li) => STAGES.includes(li.textContent));
    expect(names.map((li) => li.textContent)).toEqual(STAGES);
    expect(tessaly.queryByText(/%/)).not.toBeInTheDocument();
  });

  it("marks only the current stage, in weight as well as for assistive technology", () => {
    show("/signal/ai-on/feed/for-you");
    const steps = card(TESSALY)
      .getAllByRole("listitem")
      .filter((li) => li.getAttribute("aria-current") === "step");
    expect(steps.map((li) => li.textContent)).toEqual(["In-depth review"]);
    expect(steps[0]?.className).toContain("font-semibold");
  });

  it("draws a case at its last stage as full, with its delivered decision text", () => {
    show("/signal/main/feed/saved");
    const done = card(CLEARANCE);
    expect(done.getByText("Stage 4 of 4")).toBeInTheDocument();
    expect(done.getByText("Decision: cleared with conditions")).toBeInTheDocument();
    const bar = done.getByRole("progressbar");
    expect(bar).toHaveAttribute(
      "aria-valuetext",
      "Stage 4 of 4: Decision: cleared with conditions",
    );
    expect(bar.firstElementChild).toHaveStyle({ width: "100%" });
    const current = done
      .getAllByRole("listitem")
      .filter((li) => li.getAttribute("aria-current") === "step");
    expect(current.map((li) => li.textContent)).toEqual(["Decision"]);
  });

  it("draws the Oakhaven notice at stage 2 of 4", () => {
    show("/signal/main/feed/latest");
    expect(card(OAKHAVEN).getByText("Stage 2 of 4")).toBeInTheDocument();
    expect(card(OAKHAVEN).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0.5");
  });

  it("draws no tracker on a story with no stage", () => {
    show("/signal/main/feed/for-you");
    expect(
      card("Corvane Packaging to close two plants as volumes fall").queryByRole("progressbar"),
    ).not.toBeInTheDocument();
  });
});

describe("the rating move", () => {
  it("draws two groups for a downgrade with an outlook change, read as from, to and the word", () => {
    show("/signal/main/feed/for-you");
    const moves = card(HALVORSEN).getAllByRole("img");
    expect(moves.map((m) => m.getAttribute("aria-label"))).toEqual([
      "BB- to B+, Downgrade, one notch",
      "Negative to Stable, Outlook",
    ]);
    expect(moves[0]).toHaveTextContent("BB-B+Downgrade, one notch");
    expect(moves[1]).toHaveTextContent("NegativeStableOutlook");
  });

  it("draws an affirmed rating as delivered, with its outlook change", () => {
    show("/signal/main/topic/shipping");
    const moves = card(AFFIRM).getAllByRole("img");
    expect(moves.map((m) => m.getAttribute("aria-label"))).toEqual([
      "BB to BB, Affirmed",
      "Stable to Positive, Outlook",
    ]);
  });

  it("keeps the arrow decorative and draws nothing for a story with no move", () => {
    show("/signal/main/feed/for-you");
    expect(card(HALVORSEN).getAllByRole("img")[0]?.querySelector("svg")).toHaveAttribute(
      "aria-hidden",
      "true",
    );
    expect(card(TESSALY).queryByRole("img")).not.toBeInTheDocument();
  });
});

describe("the digest card", () => {
  it("draws an unread AI digest: labels, name, date, unread, title link, numbered points, summary", () => {
    show("/signal/ai-on/feed/for-you");
    const weekly = card(WEEKLY);
    expect(weekly.getByText("Digest")).toBeInTheDocument();
    expect(weekly.getByText("AI")).toBeInTheDocument();
    expect(weekly.getByText("Weekly brief")).toBeInTheDocument();
    expect(weekly.getByText("Fri 13 Nov")).toBeInTheDocument();
    expect(weekly.getByText("Unread")).toBeInTheDocument();
    expect(weekly.getByRole("link", { name: WEEKLY })).toHaveAttribute(
      "href",
      "#/signal/ai-on/digest/weekly-brief",
    );
    const points = weekly.getAllByRole("listitem");
    expect(points.map((li) => li.textContent)).toEqual([
      "1Packaging issuers are cutting capacity, not prices",
      "2Two telecoms disposals are now in in-depth review",
      "3Shipping downgrades cluster around 2027 maturities",
    ]);
    expect(weekly.getByText("5 points from 41 stories")).toBeInTheDocument();
    expect(weekly.getByRole("link", { name: `Read the digest: ${WEEKLY}` })).toHaveAttribute(
      "href",
      "#/signal/ai-on/digest/weekly-brief",
    );
  });

  it("links each card to the page of the digest it is an issue of, not to its own id", () => {
    show("/signal/ai-on/feed/for-you");
    expect(card(DAILY).getByRole("link", { name: DAILY })).toHaveAttribute(
      "href",
      "#/signal/ai-on/digest/daily-ratings",
    );
  });

  it("draws a read digest with no unread mark", () => {
    show("/signal/ai-on/feed/for-you");
    const daily = card(DAILY);
    expect(daily.queryByText("Unread")).not.toBeInTheDocument();
    expect(daily.getByText("Thu 12 Nov")).toBeInTheDocument();
    expect(daily.getAllByRole("listitem")).toHaveLength(2);
    expect(daily.getByText("2 points from 7 stories")).toBeInTheDocument();
  });

  it("draws a nothing-to-report digest as one sentence with no list, no AI badge and no link", () => {
    show("/signal/ai-on/feed/for-you");
    const none = card(NOTHING);
    expect(
      none.getByText(
        "Nothing material to report: no rating action reached this digest's sources on 11 November.",
      ),
    ).toBeInTheDocument();
    expect(none.getByText("Digest")).toBeInTheDocument();
    expect(none.queryByText("AI")).not.toBeInTheDocument();
    expect(none.queryByRole("list")).not.toBeInTheDocument();
    expect(none.queryByRole("link")).not.toBeInTheDocument();
  });

  it("carries the AI badge on the AI digests only", () => {
    show("/signal/ai-on/feed/for-you");
    const withBadge = [WEEKLY, DAILY, NOTHING].filter((h) => card(h).queryByText("AI") !== null);
    expect(withBadge).toEqual([WEEKLY, DAILY]);
  });

  it("draws no digest where the scene holds none (AI off)", () => {
    show("/signal/main/feed/for-you");
    expect(screen.queryByText("Digest")).not.toBeInTheDocument();
    expect(screen.queryByText("AI")).not.toBeInTheDocument();
  });

  it("puts the digest among the stories in the order the view gives", () => {
    show("/signal/ai-on/feed/for-you");
    expect(
      screen
        .getAllByRole("article")
        .map((a) => within(a).getByRole("heading", { level: 2 }).textContent),
    ).toEqual([
      "Corvane Packaging to close two plants as volumes fall",
      TESSALY,
      HALVORSEN,
      WEEKLY,
      "Brightwell Foods extends its term loan by three years",
      DAILY,
      NOTHING,
    ]);
  });
});

describe("lists that repeat a text", () => {
  /** React reports two children with one key on the console; the lists are keyed by position. */
  function keyClashes(draw: () => void): unknown[] {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    draw();
    const clashes = spy.mock.calls.filter((c) => String(c[0]).includes("same key"));
    spy.mockRestore();
    return clashes;
  }

  it("keys the numbered points by position", () => {
    expect(
      keyClashes(() =>
        render(
          <NumberedPanel
            items={[
              { number: "1", lead: "Same point" },
              { number: "2", lead: "Same point" },
            ]}
          />,
        ),
      ),
    ).toEqual([]);
  });

  it("keys the tags by position", () => {
    expect(keyClashes(() => render(<Tags tags={["Telecoms", "Telecoms"]} />))).toEqual([]);
  });

  it("keys the stage names by position", () => {
    const stage = {
      current: "Opened",
      label: "Stage 1 of 2",
      position: 0.5,
      stages: [
        { name: "Opened", current: true },
        { name: "Opened", current: false },
      ],
    };
    expect(keyClashes(() => render(<StageProgress stage={stage} />))).toEqual([]);
  });
});
