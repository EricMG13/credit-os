import type { LoadResult } from "./data";

export function App({ result }: { result: LoadResult }) {
  switch (result.kind) {
    case "missing":
      return <p className="p-6 text-slate-700">Library data is missing</p>;
    case "newer":
      return <p className="p-6 text-slate-700">This library was written by a newer version</p>;
    case "ok":
      if (result.data.issuers.length === 0) {
        return <p className="p-6 text-slate-700">No runs yet</p>;
      }
      return (
        <main className="p-6">
          {result.data.issuers.map((issuer) => (
            <section key={issuer.id}>
              <h1 className="text-xl font-semibold text-slate-900">{issuer.name}</h1>
            </section>
          ))}
        </main>
      );
  }
}
