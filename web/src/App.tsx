import { SLICE_KEYS, type LoadResult, type SliceKey } from "./data";
import { Kit } from "./pages/Kit";
import { matchRoute, routeTable, type RouteTable } from "./pages/route-table";
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

function LibraryBody({ result }: { result: LoadResult }) {
  switch (result.kind) {
    case "missing":
      return <p className="text-text-secondary">Library data is missing</p>;
    case "newer":
      return <p className="text-text-secondary">This library was written by a newer version</p>;
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

/** A route belongs to the group named by its first path segment, the library when none is. */
function areaOf(routePath: string): SliceKey {
  const first = routePath.split("/")[1];
  return SLICE_KEYS.find((key) => key === first) ?? "library";
}

function Page({ result, table, route }: { result: LoadResult; table: RouteTable; route: string }) {
  const matched = matchRoute(route, table.routes);
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
