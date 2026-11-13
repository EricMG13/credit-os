import type { LoadResult } from "./data";
import { Kit } from "./pages/Kit";
import { useHashRoute } from "./route";

export function App({ result }: { result: LoadResult }) {
  const route = useHashRoute();
  if (route === "/kit") return <Kit />;
  switch (result.kind) {
    case "missing":
      return <p className="p-6 text-text-secondary">Library data is missing</p>;
    case "newer":
      return <p className="p-6 text-text-secondary">This library was written by a newer version</p>;
    case "ok":
      if (result.data.issuers.length === 0) {
        return <p className="p-6 text-text-secondary">No runs yet</p>;
      }
      return (
        <main className="p-6">
          {result.data.issuers.map((issuer) => (
            <section key={issuer.id}>
              <h1 className="text-xl font-semibold text-text-primary">{issuer.name}</h1>
            </section>
          ))}
        </main>
      );
  }
}
