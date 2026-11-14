import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen, within } from "@testing-library/react";
import { App } from "../../../App";
import type { LoadResult } from "../../../data";

const fixture = JSON.parse(
  readFileSync(path.join(import.meta.dirname, "../../../../fixtures/run.json"), "utf8"),
) as { slice: { drafts: { id: string; files?: { name: string }[] }[] } };

function show(hash: string, run: unknown) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = { kind: "ok", data: { schema: "credit-os-data/1", issuers: [], run } };
  return render(<App result={result} />);
}
afterEach(() => {
  window.location.hash = "";
});

const REASON =
  "Not available here: this page shows a saved example and is not connected to the run service.";

describe("Documents, no documents (frame 01)", () => {
  beforeEach(() => {
    show("/run/start/no-documents", fixture.slice);
  });

  it("draws the heading, the sentence, the drop zone and its hint", () => {
    expect(screen.getByRole("heading", { level: 2, name: "Documents" })).toBeVisible();
    expect(
      screen.getByText(
        "Annual and interim reports, the credit agreement, and anything else the analysis should read.",
      ),
    ).toBeVisible();
    expect(screen.getByText(/Click to upload/)).toBeVisible();
    expect(screen.getByText("or drag and drop")).toBeInTheDocument();
    expect(screen.getByText("PDF, DOCX, HTML or XLSX, up to 50 MB each")).toBeVisible();
  });

  it("draws the empty state with a disabled action", () => {
    expect(screen.getByRole("heading", { level: 3, name: "No documents yet" })).toBeVisible();
    expect(
      screen.getByText(
        "Add at least one annual report or set of accounts. The run reads only what you add here.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Choose files" })).toBeDisabled();
  });

  it("says why uploading is unavailable, once, and ties it to the controls", () => {
    expect(screen.getAllByText(REASON)).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Choose files" })).toHaveAccessibleDescription(
      REASON,
    );
    const upload = screen.getByRole("button", { name: /Click to upload/ });
    expect(upload).toBeDisabled();
    expect(upload).toHaveAccessibleDescription(REASON);
    expect(document.querySelector("input[type='file']")).toBeNull();
    expect(screen.queryByRole("list", { name: "Documents added" })).toBeNull();
  });
});

describe("Documents, with files (frame 02)", () => {
  beforeEach(() => {
    show("/run/start/documents", fixture.slice);
  });
  const rows = () =>
    within(screen.getByRole("list", { name: "Documents added" })).getAllByRole("listitem");

  it("draws one row per file in slice order with its size and state word", () => {
    const expected = [
      ["TransDigm Group annual report FY2025.pdf", "4.8 MB", "Read in full"],
      ["TransDigm Group quarterly report Q3 FY2026.pdf", "2.1 MB", "Read in full"],
      ["Credit agreement, latest amendment.pdf", "1.3 MB", "Uploading"],
      ["Segment data FY2021 to FY2025.xlsx", "310 KB", "Read in part"],
      ["Investor presentation, scanned.pdf", "18.4 MB", "Unreadable"],
    ];
    expect(rows()).toHaveLength(5);
    rows().forEach((li, i) => {
      const [name, size, state] = expected[i] ?? [];
      expect(within(li).getByText(name ?? "")).toBeVisible();
      expect(within(li).getByText(size ?? "")).toBeVisible();
      expect(within(li).getByText(state ?? "")).toBeVisible();
    });
    expect(within(rows()[0] as HTMLElement).getByText("PDF")).toBeVisible();
    expect(within(rows()[3] as HTMLElement).getByText("XLSX")).toBeVisible();
  });

  it("draws bars for the read and uploading files only", () => {
    expect(
      within(screen.getByRole("list", { name: "Documents added" })).getAllByRole("progressbar"),
    ).toHaveLength(3);
    expect(within(rows()[2] as HTMLElement).getByRole("progressbar")).toHaveAccessibleName("62%");
    expect(within(rows()[0] as HTMLElement).getByRole("progressbar")).toHaveAccessibleName("100%");
    expect(within(rows()[3] as HTMLElement).queryByRole("progressbar")).toBeNull();
    expect(within(rows()[4] as HTMLElement).queryByRole("progressbar")).toBeNull();
  });

  it("shows the exact sentence for the part-read and unreadable files", () => {
    expect(
      within(rows()[3] as HTMLElement).getByText(
        "Two of five sheets were read. The other three hold charts only, with no figures to read.",
      ),
    ).toBeVisible();
    expect(
      within(rows()[4] as HTMLElement).getByText(
        "This PDF is a scan with no readable text, so the run cannot read it. Replace it with a text version, or remove it to continue.",
      ),
    ).toBeVisible();
    expect(screen.getAllByText(/charts only|scan with no readable text/)).toHaveLength(2);
  });

  it("offers Replace file on the unreadable row only, disabled", () => {
    expect(screen.getAllByRole("button", { name: "Replace file" })).toHaveLength(1);
    const bad = within(rows()[4] as HTMLElement);
    expect(bad.getByRole("button", { name: "Replace file" })).toBeDisabled();
    expect(bad.getByRole("button", { name: "Remove" })).toBeDisabled();
  });

  it("names each remove control by its file, disabled, with the reason as description", () => {
    const names = [
      "Remove TransDigm Group annual report FY2025.pdf",
      "Remove TransDigm Group quarterly report Q3 FY2026.pdf",
      "Remove Credit agreement, latest amendment.pdf",
      "Remove Segment data FY2021 to FY2025.xlsx",
      "Remove Investor presentation, scanned.pdf",
    ];
    names.forEach((name) => {
      const b = screen.getByRole("button", { name });
      expect(b).toBeDisabled();
      expect(b).toHaveAccessibleDescription(REASON);
    });
    expect(screen.getAllByText(REASON)).toHaveLength(1);
  });

  it("marks only the unreadable row as the error row and pulses nothing while uploading", () => {
    expect(rows().filter((li) => li.hasAttribute("data-error"))).toEqual([rows()[4]]);
    expect(within(rows()[2] as HTMLElement).getByText("Uploading")).toBeVisible();
    expect(document.querySelector(".status-halo")).toBeNull();
  });

  it("gives the file kind a readable band and a spoken kind once per row", () => {
    const first = rows()[0] as HTMLElement;
    const band = within(first).getByText("PDF");
    expect(band).toHaveClass("bg-primary-solid", "text-white");
    expect(band.closest("[aria-hidden='true']")).not.toBeNull();
    expect(within(first).getByText("PDF file:")).toHaveClass("sr-only");
  });
});

describe("Documents, long name", () => {
  it("renders a 180-character file name in full", () => {
    const name = `${"Long synthetic document name ".repeat(6)}end.pdf`.slice(0, 180);
    expect(name).toHaveLength(180);
    const source = structuredClone(fixture.slice);
    const draft = source.drafts.find((d) => d.id === "documents");
    const first = draft?.files?.[0];
    if (first === undefined) throw new Error("fixture has no first file");
    first.name = name;
    show("/run/start/documents", source);
    const nameEl = screen.getByText(name);
    expect(nameEl).toBeVisible();
    expect(nameEl).toHaveClass("wrap-anywhere");
    expect(nameEl.className).not.toMatch(/truncate|line-clamp/);
    expect(screen.getByRole("button", { name: `Remove ${name}` })).toBeInTheDocument();
  });
});
