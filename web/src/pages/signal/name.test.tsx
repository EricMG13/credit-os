// The name dialog: wording from the predecessor, focus from the lessons, no write anywhere.
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import fixture from "../../../fixtures/signal.json";
import { App } from "../../App";
import type { LoadResult } from "../../data";
import { initialsOf } from "./NameDialog";

function show(scene: string) {
  window.location.hash = `#/signal/${scene}/feed/for-you`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], signal: fixture.slice },
  };
  return render(<App result={result} />);
}

const click = (el: HTMLElement) => fireEvent.click(el);
const type = (value: string) => fireEvent.change(field(), { target: { value } });
const escape = () => fireEvent.keyDown(field(), { key: "Escape" });
const gone = () =>
  waitFor(() => {
    expect(dialog()).toBeNull();
  });
const dialog = () => screen.queryByRole("dialog", { name: "Your name" });
const chip = () => screen.getByRole("button", { name: /Writer/, hidden: true });
const field = () =>
  within(screen.getByRole("dialog")).getByRole("textbox", { name: /Display name/ });

describe("the name dialog", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("opens on arrival in no-name with the predecessor's wording and focus in the field", () => {
    show("no-name");
    const box = screen.getByRole("dialog", { name: "Your name" });
    expect(
      within(box).getByText(
        "Signal shows your name next to what you save and follow. It is a display name, not a login.",
      ),
    ).toBeInTheDocument();
    expect(within(box).getByRole("button", { name: "Continue" })).toBeInTheDocument();
    expect(within(box).queryByRole("button", { name: /Cancel|Not now/ })).toBeNull();
    expect(document.activeElement).toBe(field());
    expect(chip()).toHaveTextContent("?");
  });

  it("does not open in a scene whose viewer has a name", () => {
    show("main");
    expect(dialog()).toBeNull();
  });

  it("cannot be closed with Escape on a first visit", () => {
    show("no-name");
    escape();
    expect(dialog()).not.toBeNull();
  });

  it("shows the error on an empty or blank name, keeps the dialog and focuses the field", () => {
    show("no-name");
    click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByText("Enter a name to continue.")).toBeInTheDocument();
    expect(field()).toHaveAttribute("aria-invalid", "true");
    expect(document.activeElement).toBe(field());
    type("   ");
    click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByText("Enter a name to continue.")).toBeInTheDocument();
    expect(dialog()).not.toBeNull();
  });

  it("sets the name: chip, initials, live region, closed dialog, focus on the chip", async () => {
    show("no-name");
    type("ada king-lee");
    click(screen.getByRole("button", { name: "Continue" }));
    await gone();
    expect(chip()).toHaveTextContent("ada king-lee");
    expect(chip()).toHaveTextContent("AK");
    expect(screen.getByRole("status")).toHaveTextContent("Signed in as ada king-lee");
    expect(document.activeElement).toBe(chip());
  });

  it("opens from the chip with the current name and Cancel; Cancel changes nothing", async () => {
    show("main");
    click(chip());
    expect(field()).toHaveValue("Mara L");
    type("Someone Else");
    click(screen.getByRole("button", { name: "Cancel" }));
    await gone();
    expect(chip()).toHaveTextContent("Mara L");
    expect(document.activeElement).toBe(chip());
  });

  it("closes on Escape without a change when a name is set, focus on the chip", async () => {
    show("main");
    click(chip());
    expect(document.activeElement).toBe(field());
    escape();
    await gone();
    expect(chip()).toHaveTextContent("Mara L");
    expect(document.activeElement).toBe(chip());
  });

  it("keeps the delivered initials when the name is unchanged", async () => {
    show("main");
    click(chip());
    click(screen.getByRole("button", { name: "Continue" }));
    await gone();
    expect(chip()).toHaveTextContent("Mara L");
    expect(chip()).toHaveTextContent(fixture.slice.scenes[0]?.snapshot.viewer.initials ?? "");
  });

  it("limits the field to 60 characters and states what the name is for on the chip", async () => {
    show("no-name");
    expect(field()).toHaveAttribute("maxlength", "60");
    type("x");
    click(screen.getByRole("button", { name: "Continue" }));
    chip().focus();
    expect(
      await screen.findByText(
        "A display name, not a login. It only labels what you save and follow.",
      ),
    ).toBeInTheDocument();
  });

  it.each([
    ["Ada King", "AK"],
    ["  ada  king  lee ", "AK"],
    ["7 of 9", "7O"],
    ["Zoe", "Z"],
    ["-- Émile Zola", "ÉZ"],
  ])("takes the initials of %s as %s", (name, initials) => {
    expect(initialsOf(name)).toBe(initials);
  });
});
