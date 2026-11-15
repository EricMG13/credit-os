import { fireEvent, render, screen } from "@testing-library/react";
import { ShowSources, ShowSourcesSwitch } from "./ShowSources";
import { TraceControl } from "./TraceControl";

describe("TraceControl", () => {
  // The Show sources store lives for the session, so each test starts from off through the switch.
  beforeEach(() => {
    const { unmount } = render(
      <ShowSources>
        <ShowSourcesSwitch />
      </ShowSources>,
    );
    const sw = screen.getByRole("switch", { name: "Show sources" });
    if ((sw as HTMLInputElement).checked) fireEvent.click(sw);
    unmount();
  });

  it("is a link to its address, named by the label, reachable by Tab, hidden by opacity", () => {
    render(
      <ShowSources>
        <TraceControl href="#/somewhere" label="Show the sources for this figure" />
      </ShowSources>,
    );
    const link = screen.getByRole("link", { name: "Show the sources for this figure" });
    expect(link).toHaveAttribute("href", "#/somewhere");
    expect(link.className).toContain("opacity-0");
    expect(link.className).toContain("[@media(hover:none)]:opacity-100");
    link.focus();
    expect(document.activeElement).toBe(link);
  });

  it("is revealed by the Show sources switch", () => {
    render(
      <ShowSources>
        <ShowSourcesSwitch />
        <TraceControl href="#/somewhere" label="Show the sources for this figure" />
      </ShowSources>,
    );
    fireEvent.click(screen.getByRole("switch", { name: "Show sources" }));
    expect(screen.getByRole("link").className).toMatch(/(^|\s)opacity-100/);
  });
});
