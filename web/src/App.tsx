import type { LoadResult } from "./data";
import { Kit } from "./pages/Kit";
import { useHashRoute } from "./route";
import { PageHeader } from "./shell/PageHeader";
import { Shell, type Area } from "./shell/Shell";

const NOT_BUILT: Record<string, string> = { "/model": "Model", "/run": "Run", "/signal": "Signal" };

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

export function App({ result }: { result: LoadResult }) {
  const route = useHashRoute();
  if (route === "/kit") {
    return (
      <Shell current="kit">
        <Kit />
      </Shell>
    );
  }
  const title = NOT_BUILT[route];
  if (title !== undefined) {
    return (
      <Shell current={title.toLowerCase() as Area}>
        <PageHeader title={title} />
        <p className="mt-6 text-text-secondary">Not built yet</p>
      </Shell>
    );
  }
  return (
    <Shell current="library">
      <Library result={result} />
    </Shell>
  );
}
