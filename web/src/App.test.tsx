import { render, screen } from "@testing-library/react";
import { App } from "./App";

describe("App", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("shows the component kit at #/kit, whatever the library data", () => {
    window.location.hash = "#/kit";
    render(<App result={{ kind: "missing" }} />);
    expect(screen.getByRole("heading", { level: 1, name: "Component kit" })).toBeInTheDocument();
    expect(screen.queryByText("Library data is missing")).toBeNull();
  });

  it("marks the current area in the rail", () => {
    window.location.hash = "#/kit";
    render(<App result={{ kind: "missing" }} />);
    expect(screen.getByRole("link", { name: "Kit" })).toHaveAttribute("aria-current", "page");
  });

  it.each(["model", "run", "signal"])("says #/%s is not built yet, inside the shell", (area) => {
    window.location.hash = `#/${area}`;
    render(<App result={{ kind: "missing" }} />);
    expect(screen.getByText("Not built yet")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Areas" })).toBeInTheDocument();
  });

  it("falls back to the library for an unknown hash", () => {
    window.location.hash = "#/nowhere";
    render(<App result={{ kind: "missing" }} />);
    expect(screen.getByRole("heading", { level: 1, name: "Library" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Library" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Library data is missing")).toBeInTheDocument();
  });

  it.each(["constructor", "__proto__", "toString", "hasOwnProperty"])(
    "falls back to the library for #%s",
    (name) => {
      window.location.hash = `#${name}`;
      render(<App result={{ kind: "missing" }} />);
      expect(screen.getByText("Library data is missing")).toBeInTheDocument();
    },
  );

  it("says so when there are no runs", () => {
    render(<App result={{ kind: "ok", data: { schema: "credit-os-data/1", issuers: [] } }} />);
    expect(screen.getByText("No runs yet")).toBeInTheDocument();
  });

  it("names each issuer", () => {
    render(
      <App
        result={{
          kind: "ok",
          data: { schema: "credit-os-data/1", issuers: [{ id: "tdg", name: "TransDigm" }] },
        }}
      />,
    );
    expect(screen.getByRole("heading", { name: "TransDigm" })).toBeInTheDocument();
  });

  it("says when the data file is missing", () => {
    render(<App result={{ kind: "missing" }} />);
    expect(screen.getByText("Library data is missing")).toBeInTheDocument();
  });

  it("says when the data is from a newer version", () => {
    render(<App result={{ kind: "newer", schema: "credit-os-data/2" }} />);
    expect(screen.getByRole("main").textContent).toBe(
      "LibraryThis library was written by a newer version",
    );
  });
});
