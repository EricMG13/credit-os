import { render, screen } from "@testing-library/react";
import { Tooltip, TooltipTrigger } from "./tooltip";

describe("Tooltip", () => {
  it("shows the title and the supporting text", () => {
    render(
      <Tooltip title="A title" description="Supporting words" isOpen>
        <TooltipTrigger>Trigger</TooltipTrigger>
      </Tooltip>,
    );
    const tip = screen.getByRole("tooltip");
    expect(tip).toHaveTextContent("A title");
    expect(tip).toHaveTextContent("Supporting words");
  });

  it("shows the title alone when there is no supporting text", () => {
    render(
      <Tooltip title="Only title" isOpen placement="bottom right">
        <TooltipTrigger className="extra">Trigger</TooltipTrigger>
      </Tooltip>,
    );
    expect(screen.getByRole("tooltip")).toHaveTextContent("Only title");
    expect(screen.getByRole("button", { name: "Trigger" })).toHaveClass("extra");
  });

  it("is closed until opened", () => {
    render(
      <Tooltip title="Hidden">
        <TooltipTrigger>Trigger</TooltipTrigger>
      </Tooltip>,
    );
    expect(screen.queryByRole("tooltip")).toBeNull();
  });
});
