import { SearchLg } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { ProgressBar } from "@/components/base/progress-indicators/progress-indicators";
import { StatusBadge } from "@/components/status/StatusBadge";
import type { RunRecord } from "./slice";
import { DownloadButton } from "./parts/DownloadButton";
import {
  PlainHead,
  REGISTER_CELL,
  RegisterCard,
  RegisterTable,
  SortHead,
  sortRows,
  useSort,
} from "./parts/RegisterTable";
import { Snippet } from "./parts/Snippet";
import { TableCard } from "./parts/TableCard";
import { toTableCell } from "./parts/chartCell";
import { SUBSECTION_HEADING } from "./parts/heading";

const H = "font-display text-h3 text-text-primary";

/**
 * The module timings: the Table side of the mock's gantt, in the shared card; the Chart side is not
 * drawn (the kit has no such chart), so there is no Chart or Table toggle. The state sits in the
 * table's end column as the Module state badge. A run that holds no module says so instead.
 */
function Timings({ timings }: { timings: RunRecord["timings"] }) {
  const [module, state, started, accepted, took] = timings.columns;
  if (timings.emptyText !== null) {
    const Title = SUBSECTION_HEADING;
    return (
      <EmptyState>
        <EmptyState.Header>
          <EmptyState.FeaturedIcon icon={SearchLg} />
        </EmptyState.Header>
        <EmptyState.Content>
          <EmptyState.Title as={Title}>{timings.title}</EmptyState.Title>
          <EmptyState.Description>{timings.emptyText}</EmptyState.Description>
        </EmptyState.Content>
      </EmptyState>
    );
  }
  return (
    <TableCard
      title={timings.title}
      note={timings.note}
      label={timings.title}
      size="text-h3"
      trace={null}
      head={[module, started, accepted, took]}
      endHeading={state}
      rows={timings.rows.map((row) => ({
        label: row.module,
        cells: [row.started, row.accepted, row.took].map(toTableCell),
        end: <StatusBadge set="Module state" state={row.state} />,
      }))}
    />
  );
}

/** The registers each module wrote: sorted by name on request, each with its own "Open". */
function Registers({ registers }: { registers: RunRecord["registers"] }) {
  const [sort, onSort] = useSort<"name">();
  const [name, writtenBy, rows, file, open] = registers.columns;
  const ordered = sortRows(registers.rows, sort, (row) => row.name);
  return (
    <RegisterCard
      title={registers.title}
      count={registers.count}
      description={registers.note}
      action={<DownloadButton download={registers.downloadAll} />}
    >
      <RegisterTable
        name={registers.title}
        head={
          <>
            <SortHead column="name" label={name} sort={sort} onSort={onSort} />
            <PlainHead>{writtenBy}</PlainHead>
            <PlainHead align="right">{rows}</PlainHead>
            <PlainHead>{file}</PlainHead>
            <PlainHead srOnly align="right">
              {open}
            </PlainHead>
          </>
        }
      >
        <tbody>
          {ordered.map((row) => (
            <tr key={row.name} className="border-b border-border-hairline">
              <th
                scope="row"
                className={`${REGISTER_CELL} text-left font-medium text-text-primary`}
              >
                {row.name}
              </th>
              <td className={REGISTER_CELL}>{row.writtenBy}</td>
              <td className={`${REGISTER_CELL} text-right tabular-nums`}>{row.rows}</td>
              <td className={`${REGISTER_CELL} font-mono`}>{row.file}</td>
              <td className={`${REGISTER_CELL} text-right`}>
                <DownloadButton
                  download={{ label: open, href: row.href, reason: row.reason }}
                  color="link-color"
                  open
                />
              </td>
            </tr>
          ))}
        </tbody>
      </RegisterTable>
    </RegisterCard>
  );
}

/**
 * The Record tab: when each module started and was accepted, the hashes to copy, the spend against
 * the cap, the model calls and the registers as written. Module codes, configuration names and file
 * names appear only here. Every figure is the delivered text.
 */
export function EvidenceRecord({ record }: { record: RunRecord }) {
  const Heading = SUBSECTION_HEADING;
  const { hashes, spend, calls } = record;
  return (
    <div className="flex flex-col gap-8">
      <Timings timings={record.timings} />
      <div className="grid grid-cols-1 gap-6 min-[1200px]:grid-cols-2">
        <section className="flex flex-col gap-4">
          <Heading className={H}>{hashes.title}</Heading>
          {hashes.items.map((item) => (
            <Snippet
              key={item.label}
              caption={item.label}
              kind={item.kind}
              value={item.value}
              copyLabel={item.copyLabel}
              what={item.what}
            />
          ))}
        </section>
        <section className="flex flex-col gap-4">
          <Heading className={H}>{spend.title}</Heading>
          <ProgressBar
            value={spend.progress.value}
            max={spend.progress.max}
            label={spend.progress.text}
          />
          <p className="text-small text-text-secondary">{spend.note}</p>
        </section>
      </div>
      <TableCard
        title={calls.title}
        count={calls.count}
        note={calls.note}
        label={calls.title}
        size="text-h4"
        trace={null}
        head={[...calls.columns]}
        rows={[...calls.rows, calls.total].map((row) => ({
          label: row.label,
          cells: [...row.cells],
        }))}
        tableClass="[&_tr>:nth-child(2)]:text-left [&_td:nth-child(2)]:font-mono [&_tbody_tr:last-child>*]:font-semibold"
      />
      <Registers registers={record.registers} />
    </div>
  );
}
