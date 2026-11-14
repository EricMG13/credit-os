import { ClockRewind } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import type { Changes as ChangesData } from "./slice";
import { ButtonLink } from "./parts/ButtonLink";
import { ChangeCard } from "./parts/ChangeCard";
import { RunFrame } from "./parts/RunFrame";
import { Section } from "./parts/Section";
import { overviewHref } from "./parts/links";

/** The first run on an issuer: nothing to compare with, and the way to the Overview. */
function NoEarlierRun({
  data,
  issuer,
  run,
}: {
  data: Extract<ChangesData, { kind: "none" }>;
  issuer: string;
  run: string;
}) {
  return (
    <EmptyState>
      <EmptyState.Header>
        <EmptyState.FeaturedIcon icon={ClockRewind} />
      </EmptyState.Header>
      <EmptyState.Content>
        <EmptyState.Title as="h2">{data.title}</EmptyState.Title>
        <EmptyState.Description>{data.text}</EmptyState.Description>
      </EmptyState.Content>
      <EmptyState.Footer>
        <ButtonLink href={overviewHref(issuer, run)} color="secondary">
          Open the Overview
        </ButtonLink>
      </EmptyState.Footer>
    </EmptyState>
  );
}

/** The Changes page of a run: what changed since the earlier run, one card per change. */
export function Changes({ issuer, run }: { issuer: string | undefined; run: string | undefined }) {
  return (
    <RunFrame issuer={issuer} run={run} tab="changes">
      {({ changes, id: runId }, issuerId) =>
        changes.kind === "none" ? (
          <NoEarlierRun data={changes} issuer={issuerId} run={runId} />
        ) : (
          <Section title={changes.heading} note={changes.subtitle}>
            <ul className="grid grid-cols-1 gap-6 min-[1000px]:grid-cols-3">
              {changes.changes.map((change) => (
                <ChangeCard key={change.measure} change={change} />
              ))}
            </ul>
          </Section>
        )
      }
    </RunFrame>
  );
}
