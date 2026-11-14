// Settings, Topics (mock frame 4) and Digests (frame 5). Expected wording and sample values are the
// mock frames'; the safety reasons are decision 0006 ruling 21 and decision 0003 ruling 9.
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

const page = () => within(document.getElementById("signal-content") as HTMLElement);
const tags = (name: string) =>
  within(page().getByRole("list", { name }))
    .getAllByRole("listitem")
    .map((li) => li.textContent);

afterEach(() => {
  window.location.hash = "";
});

describe("Topics (frame 4)", () => {
  it("draws each topic with its week line, keywords and kinds as tags", () => {
    show("/signal/main/settings/topics");
    expect(page().getByRole("heading", { level: 2, name: "Topics" })).toBeTruthy();
    expect(
      page().getByText(
        "A story joins a topic when its headline or summary carries one of the keywords.",
      ),
    ).toBeTruthy();
    expect(page().getByText("12 stories this week")).toBeTruthy();
    expect(page().getByText("9 stories this week")).toBeTruthy();
    expect(tags("Keywords: Shipping")).toEqual([
      "charter rates",
      "tanker",
      "container line",
      "shipowner",
      "Halvorsen Marine",
    ]);
    expect(tags("Kinds: Shipping")).toEqual(["News", "Rating actions"]);
    expect(tags("Kinds: Packaging")).toEqual(["News", "Regulatory cases", "Rating actions"]);
  });

  it("says a topic with no keywords takes every story of its kinds", () => {
    show("/signal/main/settings/topics");
    expect(page().getByText("No keywords: every story of this kind")).toBeTruthy();
    expect(page().queryByRole("list", { name: "Keywords: Rating actions" })).toBeNull();
    expect(tags("Kinds: Rating actions")).toEqual(["Rating actions"]);
  });

  it("draws New topic and Edit disabled for a writer, each tied to the reason in view", () => {
    show("/signal/main/settings/topics");
    const reason = page().getByText("Sample data: topics cannot be changed here.");
    const buttons = page().getAllByRole("button", { name: /New topic|Edit: / });
    expect(buttons.map((b) => b.textContent)).toEqual([
      "New topic",
      "Edit",
      "Edit",
      "Edit",
      "Edit",
    ]);
    for (const button of buttons) {
      expect(button).toBeDisabled();
      expect(button.getAttribute("aria-describedby")).toBe(reason.id);
    }
    expect(page().getByRole("button", { name: "Edit: Telecoms" })).toBeDisabled();
  });

  it("shows a reader the topics and no write control, not even a disabled one", () => {
    show("/signal/reader/settings/topics");
    expect(page().getByRole("heading", { level: 2, name: "Topics" })).toBeTruthy();
    expect(page().getByText("12 stories this week")).toBeTruthy();
    expect(tags("Kinds: Shipping")).toEqual(["News", "Rating actions"]);
    expect(page().queryByRole("button", { name: /New topic|Edit/ })).toBeNull();
    expect(page().queryByText(/cannot be changed here/)).toBeNull();
  });
});

describe("Digests (frame 5)", () => {
  it("draws the form as the frame does: the digest's name as the heading, then its fields", () => {
    show("/signal/main/settings/digests");
    expect(page().getByRole("heading", { level: 2, name: "Weekly brief" })).toBeTruthy();
    expect(
      page().getByText(
        "A digest is written by a model from the stories it covers, on its schedule.",
      ),
    ).toBeTruthy();
    expect(page().getByRole("textbox", { name: /^Name/ })).toHaveValue("Weekly brief");
    expect(page().getByRole("button", { name: /Covers/ }).textContent).toContain(
      "Group: Leveraged credit",
    );
    expect(page().getByText("A group's topics, or a single topic.")).toBeTruthy();
    expect(page().getByRole("button", { name: /Schedule/ }).textContent).toContain(
      "Weekly, Friday 07:00",
    );
    expect(page().getByRole("button", { name: /Length/ }).textContent).toContain("Up to 5 points");
    expect(page().getByRole("textbox", { name: /^Brief \(optional\)/ })).toHaveValue(
      "Lead with anything that changes a refinancing date. Skip price moves.",
    );
    expect(page().getByText("Plain text. Tell the model what matters to this group.")).toBeTruthy();
  });

  it("changes every field in memory and keeps the values when moving between sections", async () => {
    show("/signal/main/settings/digests");
    fireEvent.change(page().getByRole("textbox", { name: /^Name/ }), {
      target: { value: "Friday brief" },
    });
    fireEvent.change(page().getByRole("textbox", { name: /^Brief \(optional\)/ }), {
      target: { value: "Skip price moves." },
    });
    fireEvent.click(page().getByRole("button", { name: /Schedule/ }));
    fireEvent.click(screen.getByRole("option", { name: "Daily, 07:00" }));
    fireEvent.click(page().getByRole("button", { name: /Length/ }));
    fireEvent.click(screen.getByRole("option", { name: "Up to 8 points" }));
    fireEvent.click(page().getByRole("button", { name: /Covers/ }));
    fireEvent.click(screen.getByRole("option", { name: "Topic: Shipping" }));
    window.location.hash = "#/signal/main/settings/topics";
    await screen.findByRole("heading", { level: 2, name: "Topics" });
    window.location.hash = "#/signal/main/settings/digests";
    await screen.findByRole("textbox", { name: /^Name/ });
    expect(page().getByRole("textbox", { name: /^Name/ })).toHaveValue("Friday brief");
    expect(page().getByRole("textbox", { name: /^Brief \(optional\)/ })).toHaveValue(
      "Skip price moves.",
    );
    expect(page().getByRole("button", { name: /Schedule/ }).textContent).toContain("Daily, 07:00");
    expect(page().getByRole("button", { name: /Length/ }).textContent).toContain("Up to 8 points");
    expect(page().getByRole("button", { name: /Covers/ }).textContent).toContain("Topic: Shipping");
    // The heading is the delivered name: editing the field does not rename the saved digest.
    expect(page().getByRole("heading", { level: 2, name: "Weekly brief" })).toBeTruthy();
  }, 20000);

  it("draws Run once now and Save digest disabled, each tied to its reason in view", () => {
    show("/signal/main/settings/digests");
    const run = page().getByRole("button", { name: "Run once now" });
    const save = page().getByRole("button", { name: "Save digest" });
    expect(run).toBeDisabled();
    expect(save).toBeDisabled();
    expect(document.getElementById(run.getAttribute("aria-describedby") ?? "")?.textContent).toBe(
      "Running a digest calls a paid model. It stays off until the owner sets a cap.",
    );
    expect(document.getElementById(save.getAttribute("aria-describedby") ?? "")?.textContent).toBe(
      "Sample data: digests cannot be saved here.",
    );
  });

  it("says a reader's address for Digests is for writers", () => {
    show("/signal/reader/settings/digests");
    expect(page().getByText("This section is for writers")).toBeTruthy();
    expect(page().queryByRole("textbox")).toBeNull();
    expect(page().queryByRole("button", { name: /Run once now|Save digest/ })).toBeNull();
  });
});
