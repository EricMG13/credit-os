import type { RecordBlock } from "../slice";
import { InlineCell } from "./InlineCell";
import { Section } from "./Section";
import { SUBSECTION_HEADING } from "./heading";
import { TRACE_HOST, TraceControl } from "./TraceControl";

type Statement = Extract<RecordBlock, { kind: "statement" }>;

const HEAD = "bg-surface-card px-3 py-2 font-medium whitespace-nowrap text-text-tertiary";
const STICKY = "sticky left-0 bg-surface-card";

/**
 * A statement by period (R1, the HyperUI table look): the row labels stay in view while the figures
 * scroll inside the table's own region, so the page never scrolls sideways. The Bars view and the
 * trend column the predecessor had are not drawn (mock departure 5). A line the module marked
 * as emphasised is semibold, its figures only: a missing, withheld or gap cell keeps its own weight. The kit's ChartTable has no such line, so the table is drawn here.
 */
export function StatementBlock({ block }: { block: Statement }) {
  return (
    <div className={TRACE_HOST}>
      <Section
        title={block.title}
        level={SUBSECTION_HEADING}
        actions={
          block.trace === null ? undefined : (
            <TraceControl trace={block.trace} label="Show sources for this table" />
          )
        }
      >
        <div className="overflow-x-auto">
          <table className="min-w-full border-collapse text-body">
            <caption className="sr-only">{block.title}</caption>
            <thead>
              <tr className="border-b-2 border-border-hairline">
                <th scope="col" className={`${HEAD} ${STICKY} text-left`}>
                  {block.stub}
                </th>
                {block.periods.map((period) => (
                  <th key={period} scope="col" className={`${HEAD} text-right`}>
                    {period}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row) => {
                const weight = row.emphasis ? "font-semibold" : "font-medium";
                return (
                  <tr key={row.label} className="border-b border-border-hairline last:border-b-0">
                    <th scope="row" className={`${STICKY} px-3 py-2 text-left ${weight}`}>
                      {row.label}
                    </th>
                    {row.cells.map((cell, index) => (
                      <td
                        key={block.periods[index]}
                        className={`px-3 py-2 text-right whitespace-nowrap tabular-nums ${row.emphasis && cell?.kind === "value" ? "font-semibold" : ""}`}
                      >
                        <div className="flex justify-end">
                          <InlineCell cell={cell} />
                        </div>
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {block.basis === null ? null : (
          <p className="text-small text-text-tertiary">{block.basis}</p>
        )}
      </Section>
    </div>
  );
}
