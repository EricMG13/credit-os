import { readFileSync } from "node:fs";
import path from "node:path";
import { fireEvent, render, screen, within } from "@testing-library/react";
import {
  FileListItemProgressBar,
  FileUploadDropZone,
} from "@/components/application/file-upload/file-upload-base";
import { Kit } from "./Kit";

const root = path.resolve(import.meta.dirname, "..", "..", "..");
const designSystem = readFileSync(
  path.join(root, "docs", "design", "design-system.md"),
  "utf8",
).replace(/\r\n/g, "\n");
const row = (name: string): string =>
  designSystem.split("\n").find((l) => l.startsWith(`| ${name} |`)) ?? "";

// The File state set's words, read from its row in the design system's Status table:
// "Word: shape, tone. Word: shape, tone. ..."
const fileStates = (row("File state").split("|")[2] ?? "")
  .split(". ")
  .map((entry) => entry.split(":")[0]?.trim() ?? "");

describe("design system rows", () => {
  it("names the file upload forms and the four file states", () => {
    expect(row("File upload")).toContain(
      "Drop zone; per-file progress, complete, failed with retry",
    );
    expect(fileStates).toEqual(["Uploading", "Read in full", "Read in part", "Unreadable"]);
  });
});

const pdf = new File(["x"], "report.pdf", { type: "application/pdf" });

describe("File upload on the kit page", () => {
  it("shows the drop zone and one row per file state", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "File upload" });
    expect(within(region).getByText(/or drag and drop/)).toBeInTheDocument();
    const items = within(region).getAllByRole("listitem");
    expect(items).toHaveLength(4);
    fileStates.forEach((word, i) => {
      expect(within(items[i] as HTMLElement).getByText(word)).toBeInTheDocument();
    });
    expect(document.querySelector("style")).toBeNull();
  });

  it("gives the uploading row a progress bar and draws none where progress is missing", () => {
    render(<Kit />);
    const items = within(screen.getByRole("region", { name: "File upload" })).getAllByRole(
      "listitem",
    );
    const bar = within(items[0] as HTMLElement).getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "40");
    expect(bar).toHaveAccessibleName("40%");
    expect(within(items[1] as HTMLElement).getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "100",
    );
    expect(within(items[2] as HTMLElement).queryByRole("progressbar")).toBeNull();
    expect(within(items[2] as HTMLElement).queryByText(/%/)).toBeNull();
    expect(within(items[3] as HTMLElement).queryByRole("progressbar")).toBeNull();
  });

  it("gives only the unreadable row a retry button, in an error ring", () => {
    render(<Kit />);
    const items = within(screen.getByRole("region", { name: "File upload" })).getAllByRole(
      "listitem",
    );
    expect(
      within(items[3] as HTMLElement).getByRole("button", { name: "Try again" }),
    ).toBeInTheDocument();
    expect(items[3]).toHaveClass("ring-2", "ring-error");
    for (const i of [0, 1, 2]) {
      expect(
        within(items[i] as HTMLElement).queryByRole("button", { name: "Try again" }),
      ).toBeNull();
    }
  });

  it("deletes a row and puts a retried row back to uploading with no bar", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "File upload" });
    fireEvent.click(within(region).getByRole("button", { name: "Try again" }));
    const rows = within(region).getAllByRole("listitem");
    expect(within(rows[3] as HTMLElement).getByText("Uploading")).toBeInTheDocument();
    expect(within(rows[3] as HTMLElement).queryByRole("progressbar")).toBeNull();
    expect(within(rows[3] as HTMLElement).queryByRole("button", { name: "Try again" })).toBeNull();
    fireEvent.click(within(region).getByRole("button", { name: "Delete Annual report.pdf" }));
    expect(within(region).getAllByRole("listitem")).toHaveLength(3);
  });

  it("takes the drop zone's hidden input out of the Tab order and draws the controls that stay with an outline", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "File upload" });
    expect(region.querySelector("input[type='file']")).toHaveAttribute("tabindex", "-1");
    const tabStops = [...region.querySelectorAll<HTMLElement>("button, a[href], input, select")]
      .filter((el) => el.getAttribute("tabindex") !== "-1")
      .filter((el) => !el.hasAttribute("disabled"));
    expect(tabStops.length).toBeGreaterThan(0);
    for (const el of tabStops) {
      expect(el.className, el.textContent).not.toMatch(/outline-hidden|sr-only/);
      expect(el.className, el.textContent).toMatch(/focus-visible:outline-2/);
    }
  });

  it("draws the drop zone's featured icon at the source's md size", () => {
    render(<Kit />);
    const icon = screen
      .getByRole("region", { name: "File upload" })
      .querySelector("[data-dropzone] [data-featured-icon]");
    expect(icon).toHaveClass("size-10", "*:data-icon:size-5");
    expect(icon).not.toHaveClass("size-12");
  });

  it("names the chosen file on the page", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "File upload" });
    const input = region.querySelector<HTMLInputElement>("input[type='file']");
    fireEvent.change(input as HTMLInputElement, { target: { files: [pdf] } });
    expect(within(region).getByText("Chosen: report.pdf")).toBeInTheDocument();
  });
});

describe("FileUploadDropZone", () => {
  it("calls back with the file chosen through its input", () => {
    const onDropFiles = vi.fn();
    const { container } = render(<FileUploadDropZone hint="PDF only" onDropFiles={onDropFiles} />);
    const input = container.querySelector<HTMLInputElement>("input[type='file']");
    fireEvent.change(input as HTMLInputElement, { target: { files: [pdf] } });
    expect(onDropFiles).toHaveBeenCalledWith([pdf]);
  });

  it("calls back with the file dropped on it", () => {
    const onDropFiles = vi.fn();
    const { container } = render(<FileUploadDropZone hint="PDF only" onDropFiles={onDropFiles} />);
    fireEvent.drop(container.querySelector("[data-dropzone]") as HTMLElement, {
      dataTransfer: { files: [pdf] },
    });
    expect(onDropFiles).toHaveBeenCalledWith([pdf]);
  });

  it("sends a file of another type to the unaccepted callback and not the accepted one", () => {
    const onDropFiles = vi.fn();
    const onDropUnacceptedFiles = vi.fn();
    const { container } = render(
      <FileUploadDropZone
        hint="PDF only"
        accept=".pdf"
        onDropFiles={onDropFiles}
        onDropUnacceptedFiles={onDropUnacceptedFiles}
      />,
    );
    const png = new File(["x"], "chart.png", { type: "image/png" });
    fireEvent.change(container.querySelector("input[type='file']") as HTMLInputElement, {
      target: { files: [png] },
    });
    expect(onDropFiles).not.toHaveBeenCalled();
    expect(onDropUnacceptedFiles).toHaveBeenCalledWith([png]);
    expect(screen.getByText("PDF only")).toHaveClass("text-error-primary");
  });

  it("sends a file over the size limit to the size callback", () => {
    const onDropFiles = vi.fn();
    const onSizeLimitExceed = vi.fn();
    const { container } = render(
      <FileUploadDropZone
        hint="PDF only"
        maxSize={0}
        onDropFiles={onDropFiles}
        onSizeLimitExceed={onSizeLimitExceed}
      />,
    );
    fireEvent.change(container.querySelector("input[type='file']") as HTMLInputElement, {
      target: { files: [pdf] },
    });
    expect(onDropFiles).not.toHaveBeenCalled();
    expect(onSizeLimitExceed).toHaveBeenCalledWith([pdf]);
  });

  it("ignores a drop while disabled", () => {
    const onDropFiles = vi.fn();
    const { container } = render(
      <FileUploadDropZone hint="PDF only" isDisabled onDropFiles={onDropFiles} />,
    );
    fireEvent.drop(container.querySelector("[data-dropzone]") as HTMLElement, {
      dataTransfer: { files: [pdf] },
    });
    expect(onDropFiles).not.toHaveBeenCalled();
  });
});

describe("FileListItemProgressBar", () => {
  it("calls its retry and delete callbacks", () => {
    const onRetry = vi.fn();
    const onDelete = vi.fn();
    render(
      <ul>
        <FileListItemProgressBar
          name="notes.pdf"
          size="2 MB"
          state="Unreadable"
          onRetry={onRetry}
          onDelete={onDelete}
        />
      </ul>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete notes.pdf" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it("shows the caller's size text and no bar without progress", () => {
    render(
      <ul>
        <FileListItemProgressBar name="notes.pdf" size="2 MB" state="Read in part" />
      </ul>,
    );
    expect(screen.getByText("2 MB")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
  });
});
