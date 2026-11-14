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
  describe("with href", () => {
    it("is a link with the label as its name and the given href, target and rel", () => {
      render(
        <Button href="#/library" target="_blank" rel="noreferrer">
          Open the library
        </Button>,
      );
      const link = screen.getByRole("link", { name: "Open the library" });
      expect(link.tagName).toBe("A");
      expect(link).toHaveAttribute("href", "#/library");
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noreferrer");
      expect(screen.queryByRole("button")).toBeNull();
    });

    it("keeps the button's size, colour and icon styles", () => {
      render(
        <Button href="#/x" size="lg" color="secondary" iconLeading={Icon}>
          Back
        </Button>,
      );
      const link = screen.getByRole("link", { name: "Back" });
      expect(link).toHaveClass("text-md", "ring-primary", "inline-flex");
      expect(link.querySelector("[data-icon=leading]")).not.toBeNull();
      expect(link.querySelector("[data-text]")).toHaveClass("px-0.5");
    });

    it("is announced disabled and carries no href when disabled", () => {
      render(
        <Button href="#/x" isDisabled>
          Gone
        </Button>,
      );
      const link = screen.getByRole("link", { name: "Gone" });
      expect(link).toHaveAttribute("aria-disabled", "true");
      expect(link).not.toHaveAttribute("href");
      expect(link).toHaveClass("data-disabled:opacity-50", "data-disabled:cursor-not-allowed");
    });

    it("leaves a button without href as a button with no link attributes", () => {
      render(<Button>Plain</Button>);
      const button = screen.getByRole("button", { name: "Plain" });
      expect(button.tagName).toBe("BUTTON");
      expect(button).not.toHaveAttribute("href");
      expect(screen.queryByRole("link")).toBeNull();
    });
  });
});

// Class lists a Button without href rendered at origin/main (taken from that revision's
// button.tsx), frozen here: the link branch must not add classes to the plain button.
const PLAIN_BUTTON_CLASSES: [string, string][] = [
  [
    "primary",
    "group relative inline-flex h-max cursor-pointer items-center justify-center whitespace-nowrap outline-brand transition duration-100 ease-linear focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 *:data-icon:pointer-events-none *:data-icon:size-5 *:data-icon:shrink-0 *:data-icon:transition-inherit-all gap-1 rounded-lg px-3.5 py-2.5 text-sm font-semibold before:rounded-[7px] data-icon-only:p-2.5 bg-brand-solid text-white shadow-xs-skeuomorphic ring-1 ring-transparent ring-inset hover:bg-brand-solid_hover data-loading:bg-brand-solid_hover before:absolute before:inset-px before:border before:border-white/12 before:mask-b-from-0% *:data-icon:text-white/60 hover:*:data-icon:text-white/70",
  ],
  [
    "secondary",
    "group relative inline-flex h-max cursor-pointer items-center justify-center whitespace-nowrap outline-brand transition duration-100 ease-linear before:absolute focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 *:data-icon:pointer-events-none *:data-icon:size-5 *:data-icon:shrink-0 *:data-icon:transition-inherit-all gap-1 rounded-lg px-3.5 py-2.5 text-sm font-semibold before:rounded-[7px] data-icon-only:p-2.5 bg-primary text-secondary shadow-xs-skeuomorphic ring-1 ring-primary ring-inset hover:bg-primary_hover hover:text-secondary_hover data-loading:bg-primary_hover *:data-icon:text-fg-quaternary hover:*:data-icon:text-fg-quaternary_hover",
  ],
  [
    "tertiary",
    "group relative inline-flex h-max cursor-pointer items-center justify-center whitespace-nowrap outline-brand transition duration-100 ease-linear before:absolute focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 *:data-icon:pointer-events-none *:data-icon:size-5 *:data-icon:shrink-0 *:data-icon:transition-inherit-all gap-1 rounded-lg px-3.5 py-2.5 text-sm font-semibold before:rounded-[7px] data-icon-only:p-2.5 text-tertiary hover:bg-primary_hover hover:text-tertiary_hover data-loading:bg-primary_hover *:data-icon:text-fg-quaternary hover:*:data-icon:text-fg-quaternary_hover",
  ],
  [
    "link-color",
    "group relative inline-flex h-max cursor-pointer items-center whitespace-nowrap outline-brand transition duration-100 ease-linear before:absolute focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 *:data-icon:pointer-events-none *:data-icon:size-5 *:data-icon:shrink-0 *:data-icon:transition-inherit-all px-3.5 py-2.5 text-sm font-semibold before:rounded-[7px] data-icon-only:p-2.5 justify-normal rounded p-0! text-brand-secondary hover:text-brand-secondary_hover *:data-text:underline *:data-text:decoration-transparent hover:*:data-text:decoration-fg-brand-secondary_alt *:data-icon:text-fg-brand-secondary_alt hover:*:data-icon:text-fg-brand-secondary_hover gap-1 *:data-text:underline-offset-4",
  ],
  [
    "link-destructive",
    "group relative inline-flex h-max cursor-pointer items-center whitespace-nowrap transition duration-100 ease-linear before:absolute focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 *:data-icon:pointer-events-none *:data-icon:size-5 *:data-icon:shrink-0 *:data-icon:transition-inherit-all px-3.5 py-2.5 text-sm font-semibold before:rounded-[7px] data-icon-only:p-2.5 justify-normal rounded p-0! text-error-primary outline-error hover:text-error-primary_hover *:data-text:underline *:data-text:decoration-transparent hover:*:data-text:decoration-current *:data-icon:text-fg-error-secondary hover:*:data-icon:text-fg-error-primary gap-1 *:data-text:underline-offset-4",
  ],
  [
    "primary-destructive",
    "group relative inline-flex h-max cursor-pointer items-center justify-center whitespace-nowrap transition duration-100 ease-linear focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 *:data-icon:pointer-events-none *:data-icon:size-5 *:data-icon:shrink-0 *:data-icon:transition-inherit-all gap-1 rounded-lg px-3.5 py-2.5 text-sm font-semibold before:rounded-[7px] data-icon-only:p-2.5 bg-error-solid text-white shadow-xs-skeuomorphic ring-1 ring-transparent outline-error ring-inset hover:bg-error-solid_hover data-loading:bg-error-solid_hover before:absolute before:inset-px before:border before:border-white/12 before:mask-b-from-0% *:data-icon:text-white/60 hover:*:data-icon:text-white/70",
  ],
  [
    "secondary/sm/disabled",
    "group relative inline-flex h-max cursor-pointer items-center justify-center whitespace-nowrap outline-brand transition duration-100 ease-linear before:absolute focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 *:data-icon:pointer-events-none *:data-icon:size-5 *:data-icon:shrink-0 *:data-icon:transition-inherit-all gap-1 rounded-lg px-3 py-2 text-sm font-semibold before:rounded-[7px] data-icon-only:p-2 bg-primary text-secondary shadow-xs-skeuomorphic ring-1 ring-primary ring-inset hover:bg-primary_hover hover:text-secondary_hover data-loading:bg-primary_hover *:data-icon:text-fg-quaternary hover:*:data-icon:text-fg-quaternary_hover",
  ],
  [
    "primary/lg/loading",
    "group relative inline-flex h-max cursor-pointer items-center justify-center whitespace-nowrap outline-brand transition duration-100 ease-linear focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 *:data-icon:pointer-events-none *:data-icon:size-5 *:data-icon:shrink-0 *:data-icon:transition-inherit-all gap-1.5 rounded-lg px-4 py-2.5 text-md font-semibold before:rounded-[7px] data-icon-only:p-3 bg-brand-solid text-white shadow-xs-skeuomorphic ring-1 ring-transparent ring-inset hover:bg-brand-solid_hover data-loading:bg-brand-solid_hover before:absolute before:inset-px before:border before:border-white/12 before:mask-b-from-0% *:data-icon:text-white/60 hover:*:data-icon:text-white/70 pointer-events-none [&>*:not([data-icon=loading])]:opacity-0",
  ],
];

function plainButton(key: string) {
  const [color, size, state] = key.split("/");
  return (
    <Button
      color={color as "primary"}
      size={(size ?? "md") as "md"}
      isDisabled={state === "disabled"}
      isLoading={state === "loading"}
    >
      Label
    </Button>
  );
}

describe("Button without href keeps its origin/main classes", () => {
  it.each(PLAIN_BUTTON_CLASSES)("%s", (key, expected) => {
    render(plainButton(key));
    expect(screen.getByRole("button").className).toBe(expected);
  });
});
