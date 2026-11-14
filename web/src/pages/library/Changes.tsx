import { useState } from "react";
import { ClockRewind } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { ButtonGroup, ButtonGroupItem } from "@/components/base/button-group/button-group";
import type { Changes as ChangesData } from "./slice";
import { ButtonLink } from "./parts/ButtonLink";
import { ChangeCard } from "./parts/ChangeCard";
import { ChangesTable } from "./parts/ChangesTable";
import { ModuleItems } from "./parts/ModuleItems";
import { RunFrame } from "./parts/RunFrame";
import { Section } from "./parts/Section";
import { overviewHref } from "./parts/links";

type View = "cards" | "table";

function Compared({
  data,
  issuer,
  run,
}: {
  data: Extract<ChangesData, { kind: "compared" }>;
  issuer: string;
  run: string;
}) {
  const [view, setView] = useState<View>("cards");
  return (
    <div className="flex flex-col gap-8">
      <Section title={data.heading} note={data.subtitle}>
        <div className="flex flex-col gap-6">
          <div className="self-end">
            <ButtonGroup
              aria-label="Presentation"
              size="sm"
              disallowEmptySelection
              selectedKeys={[view]}
              onSelectionChange={(keys) => {
                const [key] = keys;
                if (key === "cards" || key === "table") setView(key);
              }}
            >
              <ButtonGroupItem id="cards">Cards</ButtonGroupItem>
              <ButtonGroupItem id="table">Table</ButtonGroupItem>
            </ButtonGroup>
          </div>
          {view === "cards" ? (
            <ul className="grid grid-cols-1 gap-6 min-[1000px]:grid-cols-3">
              {data.changes.map((change) => (
                <ChangeCard key={change.measure} change={change} />
              ))}
            </ul>
          ) : (
            <ChangesTable data={data} />
          )}
        </div>
      </Section>
      <Section title="Modules" note={data.modules.summary}>
        <ModuleItems items={data.modules.items} set="Change state" issuer={issuer} run={run} />
      </Section>
    </div>
  );
}

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

/** The Changes page of a run: what changed since the earlier run, as cards or a table, and per module. */
export function Changes({ issuer, run }: { issuer: string | undefined; run: string | undefined }) {
  return (
    <RunFrame issuer={issuer} run={run} tab="changes">
      {({ changes, id: runId }, issuerId) =>
        changes.kind === "none" ? (
          <NoEarlierRun data={changes} issuer={issuerId} run={runId} />
        ) : (
          <Compared data={changes} issuer={issuerId} run={runId} />
        )
      }
    </RunFrame>
  );
}
