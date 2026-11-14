import { render } from "@testing-library/react";
import { ShowSources, ShowSourcesSwitch } from "./ShowSources";

describe("Show sources switch", () => {
  it("sets the selected knob in the card surface token, not a literal white", () => {
    const { container } = render(
      <ShowSources>
        <ShowSourcesSwitch />
      </ShowSources>,
    );
    const knob = container.querySelector("span.rounded-full > span");
    expect(knob?.className).toMatch(/group-data-\[selected\]:bg-surface-card/);
    expect(knob?.className).not.toMatch(/bg-white/);
  });
});
