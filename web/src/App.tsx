import type { LoadResult, SliceKey } from "./data";
import { Kit } from "./pages/Kit";
import { areaOf, matchRoute, routeTable, type RouteTable } from "./pages/route-table";
import { SourceContext } from "./pages/source";
import { useHashRoute } from "./route";
import { PageHeader } from "./shell/PageHeader";
import { Shell, type Area } from "./shell/Shell";

const NOT_BUILT = new Map<string, { title: string; area: Area }>([
  ["/model", { title: "Model", area: "model" }],
  ["/run", { title: "Run", area: "run" }],
  ["/signal", { title: "Signal", area: "signal" }],
]);

function Library({ result }: { result: LoadResult }) {
  return (
    <>
      <PageHeader title="Library" />
      <div className="mt-6">
        <LibraryBody result={result} />
      </div>
    </>
  );
}

const NOTICE = {
  missing: "Library data is missing",
  newer: "This library was written by a newer version",
} as const;

function LibraryBody({ result }: { result: LoadResult }) {
  switch (result.kind) {
    case "missing":
    case "newer":
      return <p className="text-text-secondary">{NOTICE[result.kind]}</p>;
    case "ok":
      if (result.data.issuers.length === 0) {
        return <p className="text-text-secondary">No runs yet</p>;
      }
      return (
        <>
          {result.data.issuers.map((issuer) => (
            <section key={issuer.id}>
              <h2 className="font-display text-h3 text-text-primary">{issuer.name}</h2>
            </section>
          ))}
        </>
      );
  }
}

/** The bare addresses (one trailing slash ignored) and the group each one belongs to. */
const BARE_GROUP = new Map<string, SliceKey>([
  ["", "library"],
  ["/library", "library"],
  ["/model", "model"],
  ["/run", "run"],
  ["/signal", "signal"],
]);

/** A group's bare address is its first route with a `home`, drawn as if that address were typed. */
function bareHome(route: string, table: RouteTable): string | null {
  const group = BARE_GROUP.get(route.endsWith("/") ? route.slice(0, -1) : route);
  if (group === undefined) return null;
  return table.routes.find((r) => areaOf(r.path) === group && r.home !== undefined)?.home ?? null;
}

function Page({ result, table, route }: { result: LoadResult; table: RouteTable; route: string }) {
  const home = bareHome(route, table);
  const matched = matchRoute(home ?? route, table.routes);
  if (home !== null && matched !== null && result.kind !== "ok") {
    return (
      <Shell current={areaOf(matched.route.path)}>
        <PageHeader title={matched.route.title} />
        <p className="mt-6 text-text-secondary">{NOTICE[result.kind]}</p>
      </Shell>
    );
  }
  if (matched !== null && result.kind === "ok") {
    const area = areaOf(matched.route.path);
    const slice = table.readers[area](result.data[area]);
    if (slice.kind === "invalid") {
      return (
        <Shell current={area}>
          <PageHeader title={matched.route.title} />
          <p className="mt-6 text-text-secondary">This part of the library could not be read</p>
          <p className="mt-2 text-text-secondary">{slice.reason}</p>
        </Shell>
      );
    }
    if (matched.route.layout === "bleed") {
      return (
        <Shell current={area} bleed>
          <SourceContext.Provider value={result.data}>
            {matched.route.render(matched.params)}
          </SourceContext.Provider>
        </Shell>
      );
    }
    return (
      <Shell current={area}>
        <SourceContext.Provider value={result.data}>
          <PageHeader title={matched.route.title} />
          <div className="mt-6">{matched.route.render(matched.params)}</div>
        </SourceContext.Provider>
      </Shell>
    );
  }
  if (route === "/kit") {
    return (
      <Shell current="kit">
        <Kit />
      </Shell>
    );
  }
  const notBuilt = NOT_BUILT.get(route);
  if (matched === null && notBuilt !== undefined) {
    return (
      <Shell current={notBuilt.area}>
        <PageHeader title={notBuilt.title} />
        <p className="mt-6 text-text-secondary">Not built yet</p>
      </Shell>
    );
  }
  if (matched !== null || route === "" || route === "/") {
    return (
      <Shell current="library">
        <Library result={result} />
      </Shell>
    );
  }
  return (
    <Shell current="library">
      <PageHeader title="Page not found" />
      <p className="mt-6 text-text-secondary">No page has this address</p>
    </Shell>
  );
}

export function App({ result, table = routeTable }: { result: LoadResult; table?: RouteTable }) {
  return <Page result={result} table={table} route={useHashRoute()} />;
}
