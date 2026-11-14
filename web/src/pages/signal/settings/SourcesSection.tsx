// Settings, Sources (mock settings frame 3): the kit's dense Table, one row per source. Source,
// State and Health sort by the delivered ranks (a source with no health sorts last either way);
// Failing shows its reason under the badge. Proposing a source would write, so it is disabled with
// its reason in view.
import { useState } from "react";
import type { SortDescriptor } from "react-aria-components";
import { Plus } from "@untitledui/icons";
import { Table } from "@/components/application/table/table";
import { Button } from "@/components/base/buttons/button";
import { StatusBadge } from "@/components/status/StatusBadge";
import { WeekBars } from "../parts/WeekBars";
import type { SignalSource } from "../slice";
import { Section } from "./Section";

const REASON_ID = "signal-sources-write-reason";
const COLUMNS = ["name", "state", "health"] as const;

function order(sources: SignalSource[], sort: SortDescriptor | undefined): SignalSource[] {
  const column = COLUMNS.find((c) => c === sort?.column);
  if (column === undefined || sort === undefined) return sources;
  const sign = sort.direction === "descending" ? -1 : 1;
  return [...sources].sort((a, b) => {
    if (column === "health" && (a.health === null || b.health === null)) {
      return Number(a.health === null) - Number(b.health === null);
    }
    return sign * (a.sort[column] - b.sort[column]);
  });
}

function Small({ children }: { children: string }) {
  return <small className="mt-1 block text-xs text-text-tertiary">{children}</small>;
}

/** Called, not drawn as an element: a null result is the cell's missing health (n.a.). */
function health(source: SignalSource) {
  if (source.health === null) return null;
  const notes = [source.reason, source.healthNote].filter((n) => n !== null);
  return (
    <>
      <StatusBadge set="Signal source states" state={source.health} />
      {notes.map((n) => (
        <Small key={n}>{n}</Small>
      ))}
    </>
  );
}

export function SourcesSection({
  sources,
  weeksHeading,
}: {
  sources: SignalSource[];
  weeksHeading: string;
}) {
  const [sort, setSort] = useState<SortDescriptor | undefined>();
  return (
    <Section
      wide
      title="Sources"
      hint="Stories come only from approved sources. Anyone who writes can propose one; the owner approves."
      action={
        <Button color="primary" iconLeading={Plus} isDisabled aria-describedby={REASON_ID}>
          Propose a source
        </Button>
      }
    >
      <p id={REASON_ID} className="mb-3 text-sm text-text-tertiary">
        Sample data: sources cannot be proposed here.
      </p>
      {sources.length === 0 ? (
        <p className="text-sm text-text-tertiary">No sources yet.</p>
      ) : (
        <div className="overflow-hidden rounded-xl ring-1 ring-border-hairline">
          <Table aria-label="Sources" size="sm" sortDescriptor={sort} onSortChange={setSort}>
            <Table.Header>
              <Table.Head
                id="name"
                isRowHeader
                allowsSorting
                className="max-xl:w-1/3"
                label="Source"
              />
              <Table.Head id="state" allowsSorting label="State" />
              <Table.Head id="health" allowsSorting label="Health" />
              <Table.Head id="check" className="max-xl:hidden" label="Last check and item" />
              <Table.Head id="weeks" label={weeksHeading} />
            </Table.Header>
            <Table.Body items={order(sources, sort)}>
              {(source) => (
                <Table.Row id={source.id}>
                  <Table.Cell>
                    <b className="block font-medium text-text-primary">{source.name}</b>
                    <Small>{source.kind}</Small>
                    <div data-last-check className="xl:hidden">
                      <Small>{`Last check ${source.lastCheck ?? "n.a."}`}</Small>
                      {source.lastCheck === null ? null : (
                        <Small>{`Last item ${source.lastItem ?? "n.a."}`}</Small>
                      )}
                    </div>
                  </Table.Cell>
                  <Table.Cell>
                    <StatusBadge set="Signal source states" state={source.state} />
                    {source.stateNote === null ? null : <Small>{source.stateNote}</Small>}
                  </Table.Cell>
                  <Table.Cell>{health(source)}</Table.Cell>
                  <Table.Cell className="max-xl:hidden">
                    {source.lastCheck === null ? null : (
                      <>
                        {source.lastCheck}
                        <Small>{`Last item ${source.lastItem ?? "n.a."}`}</Small>
                      </>
                    )}
                  </Table.Cell>
                  <Table.Cell>
                    {source.weeks.length === 0 ? null : <WeekBars weeks={source.weeks} />}
                  </Table.Cell>
                </Table.Row>
              )}
            </Table.Body>
          </Table>
        </div>
      )}
    </Section>
  );
}
