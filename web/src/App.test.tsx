import { render, screen } from "@testing-library/react";
import { App } from "./App";
import type { Route, RouteTable, SliceResult } from "./pages/route-table";

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

  it("says Page not found for an unknown hash, inside the shell", () => {
    window.location.hash = "#/nowhere";
    render(<App result={{ kind: "missing" }} />);
    expect(screen.getByText("Page not found")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Areas" })).toBeInTheDocument();
    expect(screen.queryByText("Library data is missing")).toBeNull();
  });

  it.each(["/", ""])("shows the library at hash %j", (hash) => {
    window.location.hash = `#${hash}`;
    render(<App result={{ kind: "missing" }} />);
    expect(screen.getByRole("heading", { level: 1, name: "Library" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Library" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Library data is missing")).toBeInTheDocument();
  });

  it.each([
    "constructor",
    "__proto__",
    "toString",
    "hasOwnProperty",
    "/constructor",
    "/__proto__",
    "/toString",
  ])("says Page not found for #%s instead of crashing", (name) => {
    window.location.hash = `#${name}`;
    render(<App result={{ kind: "ok", data: { schema: "credit-os-data/1", issuers: [] } }} />);
    expect(screen.getByText("Page not found")).toBeInTheDocument();
  });

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

const OK_DATA = { schema: "credit-os-data/1", issuers: [] } as const;
const okResult = { kind: "ok", data: OK_DATA } as const;

function stub(path: string, text: string, extra: Partial<Route> = {}): Route {
  return {
    path,
    title: `T ${text}`,
    render: (params) => <p>{`${text} ${JSON.stringify(params)}`}</p>,
    ...extra,
  };
}

function tableOf(routes: Route[], invalid: string[] = []): RouteTable {
  const reader = (key: string) => (): SliceResult<unknown> =>
    invalid.includes(key) ? { kind: "invalid", reason: `bad ${key}` } : { kind: "absent" };
  return {
    routes,
    readers: {
      library: reader("library"),
      model: reader("model"),
      run: reader("run"),
      signal: reader("signal"),
    },
  };
}

describe("App bare group addresses", () => {
  const sig = stub("/signal/:space/feed/:tab", "SIG", { home: "/signal/main/feed/for-you" });
  const table = tableOf([sig, stub("/model/x", "MODEL")]);

  it.each(["#/signal", "#/signal/"])("draws the home route at %s and marks the rail", (hash) => {
    window.location.hash = hash;
    render(<App result={okResult} table={table} />);
    expect(screen.getByText('SIG {"space":"main","tab":"for-you"}')).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Signal" })).toHaveAttribute("aria-current", "page");
    expect(window.location.hash).toBe(hash);
  });

  it("keeps Not built yet for a group with no home", () => {
    window.location.hash = "#/model";
    render(<App result={okResult} table={table} />);
    expect(screen.getByText("Not built yet")).toBeInTheDocument();
  });

  it("reads the slice of a bare address as the home route's group, so invalid shows", () => {
    window.location.hash = "#/signal";
    render(<App result={okResult} table={tableOf([sig], ["signal"])} />);
    expect(screen.getByText("bad signal")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "T SIG" })).toBeInTheDocument();
  });

  it.each(["#", "#/", "#/library", "#/library/"])("draws the library home at %j", (hash) => {
    window.location.hash = hash;
    const lib = stub("/library/:issuer/overview", "LIB", { home: "/library/tdg/overview" });
    render(<App result={okResult} table={tableOf([lib])} />);
    expect(screen.getByText('LIB {"issuer":"tdg"}')).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Library" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByText("No runs yet")).toBeNull();
  });

  it("keeps the placeholder library when the library declares no home", () => {
    window.location.hash = "#/";
    render(<App result={okResult} table={tableOf([])} />);
    expect(screen.getByText("No runs yet")).toBeInTheDocument();
  });

  it("does not treat #/library as a page when the library has no home", () => {
    window.location.hash = "#/library";
    render(<App result={okResult} table={tableOf([])} />);
    expect(screen.getByText("Page not found")).toBeInTheDocument();
  });

  it("uses the first route that has a home", () => {
    window.location.hash = "#/run";
    const routes = [
      stub("/run/a", "NOHOME"),
      stub("/run/b", "FIRST", { home: "/run/b" }),
      stub("/run/c", "SECOND", { home: "/run/c" }),
    ];
    render(<App result={okResult} table={tableOf(routes)} />);
    expect(screen.getByText("FIRST {}")).toBeInTheDocument();
  });
});

describe("App full-bleed pages", () => {
  const bleed = stub("/signal/main", "BLEED", { layout: "bleed" });

  it("draws no h1 from App and no padding on main", () => {
    window.location.hash = "#/signal/main";
    render(<App result={okResult} table={tableOf([bleed])} />);
    expect(screen.getByText("BLEED {}")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
    expect(screen.getAllByRole("main")).toHaveLength(1);
    expect(screen.getByRole("main").className).not.toMatch(/(^|\s)p-\d/);
  });

  it("keeps the padded layout and title for an invalid slice", () => {
    window.location.hash = "#/signal/main";
    render(<App result={okResult} table={tableOf([bleed], ["signal"])} />);
    expect(screen.getByRole("heading", { level: 1, name: "T BLEED" })).toBeInTheDocument();
    expect(screen.getByText("bad signal")).toBeInTheDocument();
    expect(screen.getByRole("main").className).toMatch(/\bp-8\b/);
  });

  it("leaves a normal route with its title and padding", () => {
    window.location.hash = "#/signal/other";
    render(<App result={okResult} table={tableOf([stub("/signal/other", "NORMAL")])} />);
    expect(screen.getByRole("heading", { level: 1, name: "T NORMAL" })).toBeInTheDocument();
    expect(screen.getByRole("main").className).toMatch(/\bp-8\b/);
  });
});
