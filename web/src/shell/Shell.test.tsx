import { render, screen, within } from "@testing-library/react";
import { PageHeader } from "./PageHeader";
import { Shell, type Area } from "./Shell";

// The five areas and their hashes, as the supplement for this step names them.
const AREAS: [Area, string, string][] = [
  ["library", "Library", "#/"],
  ["model", "Model", "#/model"],
  ["run", "Run", "#/run"],
  ["signal", "Signal", "#/signal"],
  ["kit", "Kit", "#/kit"],
];

describe("Shell", () => {
  it("names every area in the rail, in order, each linking to its hash", () => {
    render(<Shell current="library">content</Shell>);
    const rail = screen.getByRole("navigation", { name: "Areas" });
    const links = within(rail).getAllByRole("link");
    expect(links.map((a) => a.getAttribute("aria-label"))).toEqual(AREAS.map(([, name]) => name));
    expect(links.map((a) => a.getAttribute("href"))).toEqual(AREAS.map(([, , href]) => href));
  });

  it.each(AREAS)("marks only %s as the current page", (area, name) => {
    render(<Shell current={area}>content</Shell>);
    const marked = screen
      .getAllByRole("link")
      .filter((a) => a.getAttribute("aria-current") === "page");
    expect(marked.map((a) => a.getAttribute("aria-label"))).toEqual([name]);
  });

  it("draws a decorative symbol with no text", () => {
    const { container } = render(<Shell current="library">content</Shell>);
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img?.getAttribute("alt")).toBe("");
    expect(img?.getAttribute("src")).toBe("./symbol.svg");
  });

  it("puts the page in one main region", () => {
    render(<Shell current="kit">page body</Shell>);
    expect(screen.getByRole("main")).toHaveTextContent("page body");
  });
});

describe("PageHeader", () => {
  it("renders one h1 with the title, the badges and the actions", () => {
    render(
      <PageHeader title="Library" badges={<span>A badge</span>} actions={<button>Act</button>} />,
    );
    expect(screen.getAllByRole("heading")).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1, name: "Library" })).toBeInTheDocument();
    expect(screen.getByText("A badge")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Act" })).toBeInTheDocument();
  });
});
