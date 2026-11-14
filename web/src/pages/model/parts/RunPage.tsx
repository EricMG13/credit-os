import type { ReactNode } from "react";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { PageHeader } from "@/shell/PageHeader";
import { useSource } from "../../source";
import { readSlice } from "../slice/read";
import type { ModelRun } from "../slice/types";
import { ModelShell, type ShellPage } from "./ModelShell";

/** A key that two runs share only when issuer and run are both equal (a joined string could collide). */
const runKey = (run: ModelRun): string => JSON.stringify([run.issuer, run.run]);

/**
 * The run a Model route's address names, inside the Model shell; an issuer or run the slice does
 * not hold draws the not found state. App has already refused an invalid slice.
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
  const run =
    slice.kind === "ok"
      ? slice.data.runs.find((r) => r.issuer === params["issuer"] && r.run === params["run"])
      : undefined;
  if (run === undefined) {
    return (
      <div className="flex flex-col gap-8 p-8">
        <PageHeader as="h1" title="Financial model" />
        <EmptyState>
          <EmptyState.Content>
            <EmptyState.Title>Not found for this run</EmptyState.Title>
            <EmptyState.Description>
              The library holds no financial model for this issuer and run.
            </EmptyState.Description>
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
  return (
    <ModelShell key={runKey(run)} run={run} current={current}>
      {children(run)}
    </ModelShell>
  );
}
