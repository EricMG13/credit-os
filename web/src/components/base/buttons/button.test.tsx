import { render, screen } from "@testing-library/react";
import { forwardRef } from "react";
import { Button } from "./button";

function Icon({ className, "data-icon": slot }: { className?: string; "data-icon"?: string }) {
  return <svg data-testid="icon" data-icon={slot} className={className} />;
}

const WrappedIcon = forwardRef<SVGSVGElement, { className?: string; "data-icon"?: string }>(
  function WrappedIcon({ className, "data-icon": slot }, ref) {
    return <svg ref={ref} data-testid="icon" data-icon={slot} className={className} />;
  },
);

describe("Button", () => {
  it("is a button of type button by default", () => {
    render(<Button>Save</Button>);
    expect(screen.getByRole("button", { name: "Save" })).toHaveAttribute("type", "button");
  });

  it("passes the type through", () => {
    render(<Button type="submit">Send</Button>);
    expect(screen.getByRole("button", { name: "Send" })).toHaveAttribute("type", "submit");
  });

  it("renders a function component icon in each slot", () => {
    render(
      <Button iconLeading={Icon} iconTrailing={Icon}>
        Both
      </Button>,
    );
    expect(screen.getAllByTestId("icon").map((el) => el.getAttribute("data-icon"))).toEqual([
      "leading",
      "trailing",
    ]);
  });

  it("renders a forwardRef icon", () => {
    render(<Button iconLeading={WrappedIcon}>Ref</Button>);
    expect(screen.getByTestId("icon")).toHaveAttribute("data-icon", "leading");
  });

  it("renders an icon element as given", () => {
    render(<Button iconLeading={<svg data-testid="el" />}>Element</Button>);
    expect(screen.getByTestId("el")).toBeInTheDocument();
  });

  it("marks an icon-only button", () => {
    render(<Button iconLeading={Icon} aria-label="Only icon" />);
    expect(screen.getByRole("button", { name: "Only icon" })).toHaveAttribute("data-icon-only");
  });

  it("shows a spinner and refuses presses while loading", () => {
    const onPress = vi.fn();
    const { container } = render(
      <Button isLoading onPress={onPress}>
        Run
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Run" });
    expect(button).toHaveAttribute("data-loading");
    expect(container.querySelector("[data-icon=loading]")).not.toBeNull();
    button.click();
    expect(onPress).not.toHaveBeenCalled();
  });

  it.each(["link-color", "link-destructive"] as const)(
    "gives the %s button no text padding and the size's underline offset",
    (color) => {
      render(
        <Button color={color} size="sm">
          Open
        </Button>,
      );
      const button = screen.getByRole("button", { name: "Open" });
      expect(button).toHaveClass("*:data-text:underline-offset-3");
      expect(button.querySelector("[data-text]")).not.toHaveClass("px-0.5");
    },
  );

  it("keeps the text padding and no underline offset on a non-link colour", () => {
    render(<Button color="secondary">Open</Button>);
    const button = screen.getByRole("button", { name: "Open" });
    expect(button.querySelector("[data-text]")).toHaveClass("px-0.5");
    expect(button.className).not.toMatch(/underline-offset/);
  });
});
