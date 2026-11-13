import { render, screen } from "@testing-library/react";
import { App } from "./App";

describe("App", () => {
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
    const { container } = render(<App result={{ kind: "newer", schema: "credit-os-data/2" }} />);
    expect(screen.getByText("This library was written by a newer version")).toBeInTheDocument();
    expect(container.textContent).toBe("This library was written by a newer version");
  });
});
