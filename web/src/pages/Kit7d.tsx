import { useState } from "react";
import type { SortDescriptor } from "react-aria-components";
import { Table } from "@/components/application/table/table";
import { ProgressBar } from "@/components/base/progress-indicators/progress-indicators";

/** A literal sample row: `figure` is the display string; `key` orders it and is never shown. */
interface SampleRow {
  name: string;
  state: string;
  figure: string | null;
  key: number | null;
}

const MODULES: SampleRow[] = [
  { name: "Capital structure", state: "Delivered", figure: "12", key: 12 },
  { name: "Liquidity", state: "Delivered", figure: "7", key: 7 },
  { name: "Covenants", state: "Delivered with gaps", figure: null, key: null },
  { name: "Peer comparison", state: "Delivered", figure: "21", key: 21 },
];

const SOURCES: SampleRow[] = [
  { name: "Annual report", state: "Read", figure: "4", key: 4 },
  { name: "Rating agency note", state: "Read", figure: "1", key: 1 },
  { name: "Lender presentation", state: "Queued", figure: "9", key: 9 },
];

/** The caller sorts: the table only reports the request. A missing key sorts last. */
function sorted(rows: SampleRow[], sort: SortDescriptor | undefined): SampleRow[] {
  if (sort?.column !== "figure") return rows;
  const direction = sort.direction === "descending" ? -1 : 1;
  return [...rows].sort((a, b) => {
    if (a.key === null || b.key === null) return Number(a.key === null) - Number(b.key === null);
    return (a.key - b.key) * direction;
  });
}

function SampleTable({
  size,
  name,
  rowHeading,
  figureHeading,
  rows,
}: {
  size: "sm" | "md";
  name: string;
  rowHeading: string;
  figureHeading: string;
  rows: SampleRow[];
}) {
  const [sort, setSort] = useState<SortDescriptor | undefined>();
  return (
    <Table aria-label={name} size={size} sortDescriptor={sort} onSortChange={setSort}>
      <Table.Header>
        <Table.Head id="name" isRowHeader label={rowHeading} />
        <Table.Head id="state" label="State" />
        <Table.Head id="figure" allowsSorting numeric label={figureHeading} />
      </Table.Header>
      <Table.Body items={sorted(rows, sort).map((r) => ({ ...r, id: r.name }))}>
        {(item) => (
          <Table.Row id={item.id}>
            <Table.Cell>{item.name}</Table.Cell>
            <Table.Cell>{item.state}</Table.Cell>
            <Table.Cell numeric>{item.figure}</Table.Cell>
          </Table.Row>
        )}
      </Table.Body>
    </Table>
  );
}

function Heading({ id, children }: { id: string; children: string }) {
  return (
    <h2 id={id} className="font-display text-h2 text-text-primary">
      {children}
    </h2>
  );
}

/** The kit's table and progress bar sections. */
export function KitTableProgress() {
  return (
    <>
      <section aria-labelledby="kit-table" className="mt-8 flex flex-col gap-4">
        <Heading id="kit-table">Table</Heading>
        <SampleTable
          size="md"
          name="Modules, md rows"
          rowHeading="Module"
          figureHeading="Findings"
          rows={MODULES}
        />
        <SampleTable
          size="sm"
          name="Sources, sm rows"
          rowHeading="Source"
          figureHeading="Items per week"
          rows={SOURCES}
        />
      </section>

      <section aria-labelledby="kit-progress" className="mt-8 flex flex-col gap-4">
        <Heading id="kit-progress">Progress bar</Heading>
        <div className="max-w-sm">
          <ProgressBar value={3} max={8} label="3 of 8" />
        </div>
      </section>
    </>
  );
}
