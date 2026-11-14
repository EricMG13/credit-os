import { BulletChart } from "@/components/chart/BulletChart";
import { DumbbellChart } from "@/components/chart/DumbbellChart";
import type { Headroom, Segments } from "../slice/types";
import { ChartCard, chartTrace } from "./shared";

/** The section's own focus ring when the index moves focus to it. */
export const JUMP_TARGET =
  "scroll-mt-4 outline-focus focus-visible:outline-2 focus-visible:outline-offset-4";

/** Headroom to covenants and rating triggers: one bar per measure against its dashed level. */
export function HeadroomSection({ id, data }: { id: string; data: Headroom }) {
  return (
    <section id={id} tabIndex={-1} aria-label={data.title} className={JUMP_TARGET}>
      <ChartCard>
        <BulletChart
          title={data.title}
          as="h3"
          subtitle={data.subtitle}
          note={data.note}
          actions={chartTrace(data.trace, data.title)}
          rows={data.rows.map((row) => ({
            label: row.label,
            sub: row.sub,
            value: row.value,
            target: row.target,
            axisMax: row.axisMax,
            text: row.text,
          }))}
          table={{
            head: data.head,
            rows: data.rows.map((row) => ({ label: row.label, cells: row.cells })),
          }}
        />
      </ChartCard>
    </section>
  );
}

/** EBITDA margin by segment: an earlier and a later mark per row on one shared axis. */
export function SegmentsSection({ id, data }: { id: string; data: Segments }) {
  return (
    <section id={id} tabIndex={-1} aria-label={data.title} className={JUMP_TARGET}>
      <ChartCard>
        <DumbbellChart
          title={data.title}
          as="h3"
          subtitle={data.subtitle}
          note={data.note}
          actions={chartTrace(data.trace, data.title)}
          names={data.names}
          axis={data.axis}
          rows={data.rows.map((row) => ({
            label: row.label,
            from: row.from,
            to: row.to,
            text: row.text,
          }))}
          table={{
            head: data.head,
            rows: data.rows.map((row) => ({ label: row.label, cells: row.cells })),
          }}
        />
      </ChartCard>
    </section>
  );
}
