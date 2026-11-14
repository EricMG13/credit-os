import { render } from "@testing-library/react";
import { SHAPES, StatusShape } from "./shapes";

describe("status shape size", () => {
  it("draws the dashed ring 12 by 12 with a 2px stroke", () => {
    const { container } = render(<StatusShape shape="dashed ring" />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("width", "12");
    expect(svg).toHaveAttribute("height", "12");
    expect(container.querySelector("circle")).toHaveAttribute("stroke-width", "2");
  });

  it("draws the other nine shapes 10 by 10", () => {
    for (const shape of SHAPES.filter((s) => s !== "dashed ring")) {
      const { container } = render(<StatusShape shape={shape} />);
      const svg = container.querySelector("svg");
      expect(svg, shape).toHaveAttribute("width", "10");
      expect(svg, shape).toHaveAttribute("height", "10");
    }
  });
});
