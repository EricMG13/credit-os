import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen, within } from "@testing-library/react";
import { SearchLg } from "@untitledui/icons";
import { Alert, Callout } from "@/components/alert/Alert";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { Kit } from "./Kit";

const designSystem = readFileSync(
  path.resolve(import.meta.dirname, "..", "..", "..", "docs", "design", "design-system.md"),
  "utf8",
).replace(/\r\n/g, "\n");
const row = (name: string): string =>
  designSystem.split("\n").find((l) => l.startsWith(`| ${name} |`)) ?? "";

// The status shape each tone carries, quoted from the design system's Status table.
const SHAPE_OF_TONE: Record<string, string> = {
  success: "filled circle",
  warning: "triangle",
  error: "diamond",
  info: "ring",
};

describe("design system rows", () => {
  it("names the alert tones, the empty-state parts and the featured icon theme", () => {
    expect(row("Alert")).toContain("info, warning, error, success, each with its status shape");
    expect(row("Empty state")).toContain("Featured icon, title, one sentence, optional action");
    expect(row("Featured icon")).toContain("`light` theme");
  });

  it("pairs each alert tone with its status shape in the Status table", () => {
    for (const [tone, shape] of Object.entries(SHAPE_OF_TONE)) {
      const line = designSystem
        .split("\n")
        .find((l) => l.toLowerCase().startsWith(`| ${tone} | ${shape} |`));
      expect(line, `${tone} ${shape}`).toBeDefined();
    }
  });
});

describe("Alert", () => {
  it.each(Object.keys(SHAPE_OF_TONE))("draws the %s tone with its shape and colours", (tone) => {
    const { container } = render(
      <Alert tone={tone as "success"} title="Heading">
        Body text.
      </Alert>,
    );
    const alert = screen.getByText("Heading").closest("[role]");
    expect(alert).toHaveClass(`border-${tone}-edge`, `bg-${tone}-fill`);
    expect(screen.getByText("Body text.")).toHaveClass(`text-${tone}-text`);
    expect(container.querySelector(`[data-shape="${SHAPE_OF_TONE[tone] ?? ""}"]`)).not.toBeNull();
    expect(container.querySelector(`.text-${tone}-mark`)).not.toBeNull();
  });

  it("is an alert for error and warning and a status otherwise", () => {
    render(
      <>
        <Alert tone="error" title="E" />
        <Alert tone="warning" title="W" />
        <Alert tone="success" title="S" />
        <Alert tone="info" title="I" />
      </>,
    );
    expect(screen.getAllByRole("alert")).toHaveLength(2);
    expect(screen.getAllByRole("status")).toHaveLength(2);
  });

  it("shows an action and no dismiss button", () => {
    render(
      <Alert tone="info" title="Run started" action={<button type="button">Open run</button>}>
        The run is queued.
      </Alert>,
    );
    expect(screen.getByRole("button", { name: "Open run" })).toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(1);
  });
});

describe("Alert tone word", () => {
  it("names the tone before the title for assistive technology", () => {
    render(<Alert tone="error" title="The service could not be reached" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Error: The service could not be reached");
    expect(screen.getByText("Error:", { exact: false, selector: ".sr-only" })).toBeInTheDocument();
  });
});

describe("Callout", () => {
  it("wraps the status shape in a size-6 icon box", () => {
    const { container } = render(<Callout title="T">B</Callout>);
    const box = container.querySelector("[data-shape]")?.closest(".size-6");
    expect(box).toHaveClass("flex", "items-center", "justify-center");
  });

  it("is static, in the info colours and in the body type", () => {
    render(<Callout title="What would change the view">A covenant breach.</Callout>);
    const note = screen.getByRole("note");
    expect(note).toHaveClass("border-s-4", "bg-info-fill");
    expect(within(note).getByText("What would change the view")).toBeInTheDocument();
    expect(within(note).getByText("A covenant breach.")).toHaveClass("text-body", "text-info-text");
    expect(within(note).queryByRole("button")).toBeNull();
  });
});

describe("Kit sections for featured icon, empty state, alert and callout", () => {
  it("shows a featured icon in each colour", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Featured icon" });
    for (const word of ["Brand", "Gray", "Error", "Warning", "Success"]) {
      expect(within(region).getByText(word), word).toBeInTheDocument();
    }
    expect(region.querySelectorAll("[data-featured-icon]")).toHaveLength(5);
    const colourClass: Record<string, string> = {
      Brand: "bg-brand-secondary",
      Gray: "bg-tertiary",
      Error: "bg-error-secondary",
      Warning: "bg-warning-secondary",
      Success: "bg-success-secondary",
    };
    for (const [word, cls] of Object.entries(colourClass)) {
      const icon = within(region)
        .getByText(word)
        .parentElement?.querySelector("[data-featured-icon]");
      expect(icon, word).toHaveClass(cls);
    }
  });

  it("keeps the source's small default size and the kit asks for lg", () => {
    render(<FeaturedIcon color="gray" icon={SearchLg} />);
    expect(document.querySelector("[data-featured-icon]")).toHaveClass(
      "size-8",
      "*:data-icon:size-4",
      "*:data-icon:stroke-[2.25px]",
    );
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Featured icon" });
    for (const icon of region.querySelectorAll("[data-featured-icon]")) {
      expect(icon).toHaveClass("size-12");
    }
  });

  it("shows the empty state with and without an action", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Empty state" });
    expect(within(region).getAllByRole("heading", { level: 3 })).toHaveLength(2);
    expect(within(region).getAllByRole("button")).toHaveLength(1);
    expect(within(region).getByRole("button", { name: "Add sources" })).toBeEnabled();
    expect(region.querySelectorAll("[data-featured-icon]")).toHaveLength(2);
  });

  it("shows the four alert tones, one with an action", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Alert" });
    expect(within(region).getAllByRole("alert")).toHaveLength(2);
    expect(within(region).getAllByRole("status")).toHaveLength(2);
    for (const shape of Object.values(SHAPE_OF_TONE)) {
      expect(region.querySelectorAll(`[data-shape="${shape}"]`), shape).toHaveLength(1);
    }
    expect(within(region).getAllByRole("button")).toHaveLength(1);
  });

  it("shows the callout", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Callout" });
    expect(within(region).getByRole("note")).toBeInTheDocument();
  });
});
