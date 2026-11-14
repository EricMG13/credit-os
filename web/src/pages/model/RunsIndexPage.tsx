import { EmptyState } from "@/components/application/empty-state/empty-state";
import { PageHeader } from "@/shell/PageHeader";
import { useSource } from "../source";
import { readSlice } from "./slice/read";

/** The group's home: every run the slice holds, each a link to that run's front page. */
export function RunsIndexPage() {
  const slice = readSlice(useSource().model);
  // App refuses an invalid slice before a page is drawn; one that arrives anyway is a fault, not
  // an empty library.
  if (slice.kind === "invalid") throw new Error(slice.reason);
  const runs = slice.kind === "ok" ? slice.data.runs : [];
  return (
    <div className="flex flex-col gap-8 p-8">
      <PageHeader as="h1" title="Financial models" />
      {runs.length === 0 ? (
        <EmptyState>
          <EmptyState.Content>
            <EmptyState.Title>No model has been delivered yet</EmptyState.Title>
          </EmptyState.Content>
        </EmptyState>
      ) : (
        <ul className="flex flex-col gap-3">
          {runs.map((run, index) => (
            <li key={index}>
              <a
                href={`#/model/${encodeURIComponent(run.issuer)}/${encodeURIComponent(run.run)}/front`}
                className="flex flex-col gap-1 rounded-lg border border-border-hairline bg-surface-card p-4 outline-focus focus-visible:outline-2 focus-visible:outline-offset-2"
              >
                <span className="font-display text-h3 text-text-primary">
                  {run.header.issuerName}
                </span>
                <span className="text-small text-text-secondary">{run.header.asOf}</span>
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
