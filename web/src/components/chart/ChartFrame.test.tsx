import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChartFrame } from "./ChartFrame";

const body = () => <p>body</p>;

describe("ChartFrame", () => {
  it("without subtitle and actions the header holds only the title and the toggle", () => {
    render(<ChartFrame title="Net debt path">{body}</ChartFrame>);
    const header = screen.getByRole("radiogroup", {
      name: "Net debt path: Chart or Table",
    }).parentElement;
    expect(header?.children).toHaveLength(2);
    expect(header?.firstElementChild).toBe(screen.getByRole("heading", { name: "Net debt path" }));
    expect(screen.getByRole("figure")).not.toHaveAttribute("aria-describedby");
  });

  it("draws the subtitle and actions in the order title, subtitle, actions, toggle", () => {
    render(
      <ChartFrame
        title="Net debt path"
        subtitle="Base case, per share"
        actions={<button type="button">Trace</button>}
      >
        {body}
      </ChartFrame>,
    );
    const title = screen.getByRole("heading", { name: "Net debt path" });
    const subtitle = screen.getByText("Base case, per share");
    const action = screen.getByRole("button", { name: "Trace" });
    const toggle = screen.getByRole("radiogroup", { name: "Net debt path: Chart or Table" });
    const follows = (a: Node, b: Node) =>
      Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
    expect(follows(title, subtitle)).toBe(true);
    expect(follows(subtitle, action)).toBe(true);
    expect(follows(action, toggle)).toBe(true);
  });

  it("describes the figure by the subtitle and names it by the title only", () => {
    render(
      <ChartFrame title="Net debt path" subtitle="Base case, per share">
        {body}
      </ChartFrame>,
    );
    const figure = screen.getByRole("figure", { name: "Net debt path" });
    expect(figure).toHaveAccessibleDescription("Base case, per share");
  });

  it("draws the subtitle in the tertiary text colour, as the mock does", () => {
    render(
      <ChartFrame title="Net debt path" subtitle="Base case, per share">
        {body}
      </ChartFrame>,
    );
    expect(screen.getByText("Base case, per share")).toHaveClass("text-text-tertiary");
  });

  it("keeps the heading level the caller passes", () => {
    render(
      <ChartFrame title="Net debt path" as="h3" subtitle="Base case">
        {body}
      </ChartFrame>,
    );
    expect(screen.getByRole("heading", { level: 3, name: "Net debt path" })).toBeInTheDocument();
  });
});
