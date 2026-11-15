import { useState, type ComponentProps, type ReactElement } from "react";
import { ClockRewind, Hourglass01 } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { ButtonGroup, ButtonGroupItem } from "@/components/base/button-group/button-group";
import type { Changes as ChangesData } from "./slice";
import { Button } from "@/components/base/buttons/button";
import { ChangeCard } from "./parts/ChangeCard";
import { ChangesTable } from "./parts/ChangesTable";
import { SECTION_HEADING } from "./parts/heading";
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

/** An empty state with a titled message and the way to the Overview. */
function OverviewPrompt({
  icon,
  title,
  text,
  issuer,
  run,
}: {
  icon: ComponentProps<typeof EmptyState.FeaturedIcon>["icon"];
  title: string;
  text: string;
  issuer: string;
  run: string;
}) {
  return (
    <EmptyState>
      <EmptyState.Header>
        <EmptyState.FeaturedIcon icon={icon} />
      </EmptyState.Header>
      <EmptyState.Content>
        <EmptyState.Title as={SECTION_HEADING}>{title}</EmptyState.Title>
        <EmptyState.Description>{text}</EmptyState.Description>
      </EmptyState.Content>
      <EmptyState.Footer>
        <Button href={overviewHref(issuer, run)} color="secondary">
          Open the Overview
        </Button>
      </EmptyState.Footer>
    </EmptyState>
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
    <OverviewPrompt
      icon={ClockRewind}
      title={data.title}
      text={data.text}
      issuer={issuer}
      run={run}
    />
  );
}

/** A later run whose comparison with the earlier run has not been run yet: not the first-run state. */
function NotYetCompared({
  data,
  issuer,
  run,
}: {
  data: Extract<ChangesData, { kind: "pending" }>;
  issuer: string;
  run: string;
}) {
  return (
    <OverviewPrompt
      icon={Hourglass01}
      title={data.title}
      text={data.text}
      issuer={issuer}
      run={run}
    />
  );
}

/** The page for a run's changes state; a kind this switch lacks does not compile. */
function ChangesState({
  changes,
  issuer,
  run,
}: {
  changes: ChangesData;
  issuer: string;
  run: string;
}): ReactElement {
  switch (changes.kind) {
    case "none":
      return <NoEarlierRun data={changes} issuer={issuer} run={run} />;
    case "pending":
      return <NotYetCompared data={changes} issuer={issuer} run={run} />;
    case "compared":
      return <Compared data={changes} issuer={issuer} run={run} />;
  }
}

/** The Changes page of a run: what changed since the earlier run, as cards or a table, and per module. */
export function Changes({ issuer, run }: { issuer: string | undefined; run: string | undefined }) {
  return (
    <RunFrame issuer={issuer} run={run} tab="changes">
      {({ changes, id: runId }, issuerId) => (
        <ChangesState changes={changes} issuer={issuerId} run={runId} />
      )}
    </RunFrame>
  );
}
