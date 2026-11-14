import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen } from "@testing-library/react";
import { Blocked } from "./Blocked";
import { GapBadge } from "@/components/status/StatusBadge";
import { GapPanel } from "./GapPanel";
import { Missing } from "./Missing";
import { Skeleton } from "./Skeleton";
import { Withheld } from "./Withheld";

const designSystem = readFileSync(
  path.resolve(import.meta.dirname, "..", "..", "..", "..", "docs", "design", "design-system.md"),
  "utf8",
).replace(/\r\n/g, "\n");

// The "Gap states" table: first column the state, second its quoted wording.
const start = designSystem.indexOf("| State | Wording | Drawn as |");
const WORDS = new Map(
  designSystem
    .slice(start)
    .split("\n")
    .slice(2)
    .filter((l, i, all) => l.startsWith("|") && all.slice(0, i).every((p) => p.startsWith("|")))
    .map((l) => {
      const cells = l.split("|");
      return [(cells[1] ?? "").trim(), (cells[2] ?? "").trim().replace(/^"|"$/g, "")] as const;
    }),
);

describe("gap states table", () => {
  it("gives the four words", () => {
    expect(WORDS.get("Gap")).toBe("Not established for this run");
    expect(WORDS.get("Blocked module")).toBe("Not assessable");
    expect(WORDS.get("Missing figure")).toBe("n.a.");
    expect(WORDS.get("Withheld value")).toBe("Withheld");
  });
});

describe("GapPanel", () => {
  it("shows the gap words, the dashed ring and the reason", () => {
    const { container } = render(<GapPanel reason="No filing covers this period." />);
    expect(screen.getByText(WORDS.get("Gap") ?? "")).toBeInTheDocument();
    expect(screen.getByText("No filing covers this period.")).toBeInTheDocument();
    expect(container.querySelector('[data-shape="dashed ring"]')).not.toBeNull();
    const panel = container.firstElementChild as HTMLElement;
    expect(panel.className).toContain("gap-hatch");
    expect(panel.className).toContain("border-dashed");
    expect(panel.className).toContain("border-border-gap");
    expect(panel.className).toContain("text-gap-text");
    expect(panel.className).toContain("rounded-ds-md");
  });
});

describe("GapBadge", () => {
  it("shows the gap words with the dashed ring", () => {
    const { container } = render(<GapBadge />);
    expect(screen.getByText(WORDS.get("Gap") ?? "")).toBeInTheDocument();
    expect(container.querySelector('[data-shape="dashed ring"]')).not.toBeNull();
    const cls = (container.firstElementChild as HTMLElement).className;
    expect(cls).toContain("border-dashed");
    expect(cls).toContain("text-caption");
    expect(cls).not.toContain("text-sm");
  });
});

describe("Missing", () => {
  it("shows n.a. visibly, announces not available, and never 0", () => {
    const { container } = render(<Missing />);
    const visible = container.querySelector('[aria-hidden="true"]');
    expect(visible).toHaveTextContent(/^n\.a\.$/);
    expect(visible?.textContent).toBe(WORDS.get("Missing figure"));
    const hidden = container.querySelector(".sr-only");
    expect(hidden).toHaveTextContent("not available");
    expect(container.firstElementChild?.getAttribute("aria-label")).toBeNull();
    expect((container.firstElementChild as HTMLElement).className).toContain("text-text-tertiary");
    expect(container.textContent).not.toContain("0");
  });
});

describe("Withheld", () => {
  it("shows a striped bar and the word, with the reason when given", () => {
    const { container } = render(<Withheld reason="The issuer has not published it." />);
    expect(screen.getByText(WORDS.get("Withheld value") ?? "")).toBeInTheDocument();
    expect(container.querySelector(".withheld-stripes")).not.toBeNull();
    expect(screen.getByText("The issuer has not published it.")).toBeInTheDocument();
  });

  it("omits the reason when none is given", () => {
    const { container } = render(<Withheld />);
    expect(container.querySelector("p")).toBeNull();
  });
});

describe("Blocked", () => {
  it("shows the word, the slashed circle and the sentence", () => {
    const { container } = render(<Blocked reason="The cash-flow statement is missing." />);
    expect(screen.getByText(WORDS.get("Blocked module") ?? "")).toBeInTheDocument();
    expect(container.querySelector('[data-shape="slashed circle"]')).not.toBeNull();
    expect(screen.getByText("The cash-flow statement is missing.")).toBeInTheDocument();
  });
});

describe("Skeleton", () => {
  it("renders exactly the lines asked for, hidden, with no animation class", () => {
    const { container } = render(<Skeleton lines={4} />);
    const root = container.firstElementChild as HTMLElement;
    expect(root).toHaveAttribute("aria-hidden", "true");
    expect(root.children).toHaveLength(4);
    for (const el of [root, ...root.querySelectorAll("*")]) {
      expect(el.className).not.toContain("animate");
    }
    expect(root.children[0]?.className).toContain("rounded-ds-xs");
    expect(root.children[0]?.className).toContain("bg-surface-subtle");
  });

  it("makes the last block the short one when there is more than one line", () => {
    const { container } = render(<Skeleton lines={3} />);
    const kids = [...(container.firstElementChild?.children ?? [])];
    expect(kids.map((k) => k.className.includes("w-2/3"))).toEqual([false, false, true]);
    const one = render(<Skeleton lines={1} />).container.firstElementChild;
    expect(one?.children[0]?.className).not.toContain("w-2/3");
  });

  it("throws a RangeError unless lines is a non-negative integer", () => {
    for (const n of [-1, 2.5, Number.NaN, Number.POSITIVE_INFINITY]) {
      expect(() => render(<Skeleton lines={n} />), String(n)).toThrow(RangeError);
    }
    expect(() => render(<Skeleton lines={0} />)).not.toThrow();
  });
});
