import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PathChart } from "./PathChart";

describe("PathChart frame props", () => {
  it("passes subtitle and actions through to the frame", () => {
    render(
      <PathChart
        title="Interest cover"
        subtitle="Base case"
        actions={<button type="button">Trace</button>}
        periods={["FY24", "LTM"]}
        series={[{ name: "Base case", values: [2.8, 2.9], labels: ["2.8x", "2.9x"] }]}
        yTicks={[
          { value: 0, label: "0" },
          { value: 4, label: "4x" },
        ]}
        table={{
          head: ["Interest cover", "FY24", "LTM"],
          rows: [{ label: "Base case", cells: ["2.8x", "2.9x"] }],
        }}
      />,
    );
    expect(screen.getByText("Base case", { selector: "p" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Trace" })).toBeInTheDocument();
    expect(screen.getByRole("figure", { name: "Interest cover" })).toHaveAccessibleDescription(
      "Base case",
    );
  });
});
