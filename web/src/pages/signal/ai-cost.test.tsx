// Settings, AI and cost (mock frames 7, 8 and 9). Expected wording and sample values are the frames';
// the toggles' reason is decision 0006 ruling 21.
import { render, screen, within } from "@testing-library/react";
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

const page = () => within(document.getElementById("signal-content") as HTMLElement);
const switches = () => page().getAllByRole("switch");
const REASON = "AI parts stay off until the owner sets a cap.";
const PARTS = ["AI line on stories", "Signal strength", "Digests"];

/** A copy of the fixture whose scene `id` has spend replaced (null means no reading). */
function withSpend(id: string, spend: unknown): unknown {
  const copy = structuredClone(fixture.slice);
  const scene = copy.scenes.find((s) => s.id === id);
  if (scene === undefined) throw new Error("the fixture holds the scene");
  Object.assign(scene.snapshot.settings.ai, { spend });
  return copy;
}

afterEach(() => {
  window.location.hash = "";
});

describe("AI and cost with AI on (frame 7)", () => {
  it("draws the intro, the spend as a bar with the delivered label, its note and the switches on", () => {
    show("/signal/ai-on/settings/ai");
    expect(page().getByRole("heading", { level: 2, name: "AI and cost" })).toBeTruthy();
    expect(
      page().getByText(
        "Opening or refreshing a page never calls a model. These parts do, when a story arrives or a digest is due.",
      ),
    ).toBeTruthy();
    expect(page().getByText("Spend in November")).toBeTruthy();
    const bar = page().getByRole("progressbar");
    expect(bar).toHaveAccessibleName("USD 6.40 of USD 15.00");
    expect(page().getByText("The cap resets on 1 December.")).toBeTruthy();
    expect(page().queryByRole("alert")).toBeNull();
    expect(page().queryByRole("status")).toBeNull();
    expect(switches().map((s) => (s as HTMLInputElement).checked)).toEqual([true, true, true]);
    expect(
      page().getByText("Scheduled briefs. A digest with nothing to report makes no call."),
    ).toBeTruthy();
  });

  it("draws no percentage anywhere, and positions the bar by the delivered position only", () => {
    const { container } = show("/signal/ai-on/settings/ai");
    expect(container.textContent).not.toMatch(/\d\s*%/);
    const bar = page().getByRole("progressbar");
    expect(bar.getAttribute("aria-valuenow")).toBe("0.43");
    expect(bar.getAttribute("aria-valuemax")).toBe("1");
    expect((bar.firstElementChild as HTMLElement).style.transform).toBe("translateX(-57%)");
  });
});

describe("AI and cost with AI off (frame 8)", () => {
  it("draws the info alert with the delivered notice, the spend and every switch off", () => {
    show("/signal/main/settings/ai");
    expect(page().getByText("Opening or refreshing a page never calls a model.")).toBeTruthy();
    const alert = page().getByRole("status");
    expect(alert).toHaveTextContent("AI is off");
    expect(alert).toHaveTextContent(
      "Stories arrive with no AI line and no signal strength, and digests are paused. Nothing is spent.",
    );
    expect(page().getByRole("progressbar")).toHaveAccessibleName("USD 6.40 of USD 15.00");
    expect(page().queryByText("The cap resets on 1 December.")).toBeNull();
    expect(switches().map((s) => (s as HTMLInputElement).checked)).toEqual([false, false, false]);
    expect(page().getByText("Scheduled briefs.")).toBeTruthy();
  });
});

describe("AI and cost at its cap (frame 9)", () => {
  it("draws the warning alert saying when AI resumes, a full bar and the switches still on", () => {
    show("/signal/ai-capped/settings/ai");
    const alert = page().getByRole("alert");
    expect(alert).toHaveTextContent("AI has reached its cap for November");
    expect(alert).toHaveTextContent(
      "Stories arrive with no AI line and no signal strength, and digests are paused until 1 December. Only the owner can raise the cap.",
    );
    const bar = page().getByRole("progressbar");
    expect(bar).toHaveAccessibleName("USD 15.00 of USD 15.00");
    expect(bar.getAttribute("aria-valuenow")).toBe("1");
    expect(switches().map((s) => (s as HTMLInputElement).checked)).toEqual([true, true, true]);
  });
});

describe("the AI parts' switches", () => {
  it.each(["main", "ai-on", "ai-capped"])(
    "are present and disabled in %s, named by their parts, tied to the reason in view",
    (scene) => {
      show(`/signal/${scene}/settings/ai`);
      const reason = page().getByText(REASON);
      expect(switches()).toHaveLength(3);
      for (const [i, one] of switches().entries()) {
        expect(one).toBeDisabled();
        expect(one).toHaveAccessibleName(PARTS[i] ?? "");
        expect(one.getAttribute("aria-describedby")).toContain(reason.id);
      }
    },
  );

  it("draws no switch and no reason when a scene lists no parts", () => {
    show("/signal/no-topics/settings/ai");
    expect(page().queryByRole("switch")).toBeNull();
    expect(page().queryByText(REASON)).toBeNull();
    expect(page().getByRole("status")).toHaveTextContent("AI is off");
  });
});

describe("a spend with no reading", () => {
  it("draws n.a. in place of the bar and keeps the switches", () => {
    show("/signal/main/settings/ai", withSpend("main", null));
    expect(page().queryByRole("progressbar")).toBeNull();
    expect(page().getByText("n.a.")).toBeTruthy();
    expect(switches()).toHaveLength(3);
  });

  it("refuses a malformed AI state with its path", () => {
    show(
      "/signal/main/settings/ai",
      withSpend("main", { title: "t", label: "l", note: null, position: 2 }),
    );
    expect(
      screen.getByText(
        "scenes[0].snapshot.settings.ai.spend.position: expected a number from 0 to 1",
      ),
    ).toBeInTheDocument();
  });
});

describe("AI and cost for a reader", () => {
  it("says the section is for writers", () => {
    show("/signal/reader/settings/ai");
    expect(page().getByText("This section is for writers")).toBeTruthy();
    expect(page().queryByRole("switch")).toBeNull();
    expect(page().queryByRole("progressbar")).toBeNull();
  });
});
