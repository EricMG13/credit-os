import { useId } from "react";
import { Badge } from "@/components/base/badges/badges";
import { Tile } from "@/components/card/Card";
import type { Overview as OverviewData, Point } from "./slice";
import { BottomLine } from "./parts/BottomLine";
import { CellValue } from "./parts/CellValue";
import { MetricTile } from "./parts/MetricTile";
import { RunFrame } from "./parts/RunFrame";
import { TRACE_HOST, TraceControl } from "./parts/TraceControl";
import { SECTION_HEADING, SUBSECTION_HEADING } from "./parts/heading";

const FIGURE = "text-[40px]/11 tracking-tight tabular-nums break-words";

function PointTile({ point }: { point: Point }) {
  return (
    <li className={`${TRACE_HOST} @container`}>
      <Tile>
        <div className="flex flex-col items-start gap-3 @md:flex-row @md:gap-5">
          <div className="max-w-50 flex-none">
            <CellValue cell={point.figure} figureClass={FIGURE} />
          </div>
          <div className="flex min-w-0 flex-1 flex-col items-start gap-2">
            <p className="text-body">{point.text}</p>
            <Badge size="sm" className="max-w-full whitespace-normal">
              {point.qualifier}
            </Badge>
          </div>
          <TraceControl trace={point.trace} label="Show sources for this point" />
        </div>
      </Tile>
    </li>
  );
}

function ForAndAgainst({ sides }: { sides: OverviewData["sides"] }) {
  const Heading = SECTION_HEADING;
  const Column = SUBSECTION_HEADING;
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-6">
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <Heading id={headingId} className="font-display text-h2 text-text-primary">
          {sides.heading}
        </Heading>
        <span className="text-small text-text-tertiary">{sides.note}</span>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:gap-8">
        {sides.columns.map((column) => (
          <div key={column.name} className="flex flex-col gap-3">
            <Column className="text-h4 text-text-primary">{column.name}</Column>
            <ul className="flex flex-col gap-3">
              {column.items.map((point) => (
                <PointTile key={point.text} point={point} />
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

/** The Overview page of a run: the upper half, bottom line, headline figures, for and against. */
export function Overview({ issuer, run }: { issuer: string | undefined; run: string | undefined }) {
  return (
    <RunFrame issuer={issuer} run={run} tab="overview">
      {({ overview }) => (
        <div className="flex flex-col gap-8">
          <BottomLine text={overview.bottomLine} level={SECTION_HEADING} />
          <section aria-label={overview.metricsLabel}>
            <ul className="grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-4">
              {overview.metrics.map((metric) => (
                <MetricTile key={metric.label} metric={metric} />
              ))}
            </ul>
          </section>
          <ForAndAgainst sides={overview.sides} />
        </div>
      )}
    </RunFrame>
  );
}
