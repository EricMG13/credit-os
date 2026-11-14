import { Callout } from "@/components/alert/Alert";
import { Badge } from "@/components/base/badges/badges";
import { Tile } from "@/components/card/Card";
import { Timeline } from "@/components/timeline/Timeline";
import type { Overview as OverviewData, Point } from "./slice";
import { BottomLine } from "./parts/BottomLine";
import { CellValue } from "./parts/CellValue";
import { Findings } from "./parts/Findings";
import { MetricTile } from "./parts/MetricTile";
import { RunFrame } from "./parts/RunFrame";
import { Section } from "./parts/Section";
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
  const Column = SUBSECTION_HEADING;
  return (
    <Section title={sides.heading} note={sides.note}>
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
    </Section>
  );
}

/** What would change the view: the kit's info Callout, with its one trace control at the corner. */
function ChangeViewNote({ view }: { view: OverviewData["changeView"] }) {
  return (
    <Section title="What would change the view">
      <div className={`${TRACE_HOST} [&>[role=note]]:pr-12`}>
        <Callout title={view.title}>{view.text}</Callout>
        <span className="absolute top-3 right-3">
          <TraceControl trace={view.trace} label="Show sources for the triggers" />
        </span>
      </div>
    </Section>
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
          <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
            <Section title="Key findings">
              <Findings findings={overview.findings} />
            </Section>
            <div className="flex flex-col gap-10">
              <ChangeViewNote view={overview.changeView} />
              <Section title="Dates to watch">
                <Timeline items={overview.dates} />
              </Section>
            </div>
          </div>
        </div>
      )}
    </RunFrame>
  );
}
