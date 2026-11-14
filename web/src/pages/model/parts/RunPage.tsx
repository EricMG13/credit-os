import type { ReactNode } from "react";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { PageHeader } from "@/shell/PageHeader";
import { useSource } from "../../source";
import { readSlice } from "../slice/read";
import type { ModelRun } from "../slice/types";
import { ModelShell, type ShellPage } from "./ModelShell";

/** A key that two runs share only when issuer and run are both equal (a joined string could collide). */
export const runKey = (run: ModelRun): string => JSON.stringify([run.issuer, run.run]);

/** The group's padded frame: the page title, one statement and the way back to the index. */
function Notice({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col gap-8 p-8">
      <PageHeader as="h1" title="Financial model" />
      <EmptyState>
        <EmptyState.Content>
          <EmptyState.Title>{title}</EmptyState.Title>
          <EmptyState.Description>{description}</EmptyState.Description>
        </EmptyState.Content>
        <EmptyState.Footer>
          <a href="#/model/runs" className="text-small text-text-link">
            All financial models
          </a>
        </EmptyState.Footer>
      </EmptyState>
    </div>
  );
}

/**
 * The run a Model route's address names, inside the Model shell. A run the reader held as
 * unreadable draws why; an issuer or run the slice does not hold draws the not found state. App
 * has already refused an invalid slice.
 */
export function RunPage({
  params,
  current,
  children,
}: {
  params: Record<string, string>;
  current: ShellPage;
  children: (run: ModelRun) => ReactNode;
}) {
  const slice = readSlice(useSource().model);
  const named = (r: { issuer: string | null; run: string | null }) =>
    r.issuer === params["issuer"] && r.run === params["run"];
  const run = slice.kind === "ok" ? slice.data.runs.find(named) : undefined;
  if (run === undefined) {
    const unreadable = slice.kind === "ok" ? slice.data.unreadable.find(named) : undefined;
    return unreadable === undefined ? (
      <Notice
        title="Not found for this run"
        description="The library holds no financial model for this issuer and run."
      />
    ) : (
      <Notice title="This part of the library could not be read" description={unreadable.reason} />
    );
  }
  return (
    <ModelShell key={runKey(run)} run={run} current={current}>
      {children(run)}
    </ModelShell>
  );
}
