import { render, screen, within } from "@testing-library/react";
import { Kit } from "./Kit";

describe("Kit link button section", () => {
  it("is a named section on the kit page", () => {
    render(<Kit />);
    expect(screen.getByRole("heading", { level: 2, name: "Link button" })).toBeInTheDocument();
  });

  it("shows the link button as default, with an icon and disabled", () => {
    render(<Kit />);
    const section = within(screen.getByRole("region", { name: "Link button" }));
    expect(section.getByRole("link", { name: "Open the library" })).toHaveAttribute(
      "href",
      "#/library",
    );
    const withIcon = section.getByRole("link", { name: "Back to the library" });
    expect(withIcon.querySelector("[data-icon=leading]")).not.toBeNull();
    const disabled = section.getByRole("link", { name: "Library unavailable" });
    expect(disabled).toHaveAttribute("aria-disabled", "true");
    expect(disabled).not.toHaveAttribute("href");
  });
});
