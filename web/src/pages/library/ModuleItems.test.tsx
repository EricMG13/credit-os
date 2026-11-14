import { render, screen, within } from "@testing-library/react";
import { ModuleItems } from "./parts/ModuleItems";

const item = (title: string, module: string | null) => ({
  title,
  lead: `${title} lead`,
  state: "Delivered" as const,
  module,
});

describe("ModuleItems, the number of lists", () => {
  it("draws one list for a single item, not an empty second one", () => {
    const { container } = render(
      <ModuleItems items={[item("Recovery", "recovery")]} issuer="a" run="b" />,
    );
    expect(screen.getAllByRole("list")).toHaveLength(1);
    expect(within(screen.getByRole("list")).getAllByRole("listitem")).toHaveLength(1);
    expect(container.firstElementChild).not.toHaveClass("md:grid-cols-2");
  });

  it("splits two items into two lists of one, and three into two and one", () => {
    const two = render(
      <ModuleItems items={[item("A", null), item("B", null)]} issuer="a" run="b" />,
    );
    expect(screen.getAllByRole("list").map((list) => list.children.length)).toEqual([1, 1]);
    expect(two.container.firstElementChild).toHaveClass("md:grid-cols-2");
    two.unmount();
    render(
      <ModuleItems
        items={[item("A", null), item("B", null), item("C", null)]}
        issuer="a"
        run="b"
      />,
    );
    expect(screen.getAllByRole("list").map((list) => list.children.length)).toEqual([2, 1]);
  });
});
