import { useState } from "react";
import { GapPanel } from "@/components/gap/GapPanel";
import { CaseCards } from "./parts/CaseCards";
import { Item } from "./parts/Item";
import { Passage } from "./parts/Passage";
import { RunPage, runKey } from "./parts/RunPage";
import { TraceControl } from "./parts/TraceControl";
import { CoverCard, DriversCard, PathsCard, WalkCard } from "./sections/ForecastCharts";
import { SectionHeading, gapReason, pairGrid } from "./sections/shared";
import type { ModelRun } from "./slice/types";

/** The case is in-memory page state; the first case is the default. */
function Body({ run }: { run: ModelRun }) {
  const [chosen, setChosen] = useState(0);
  const page = run.forecast;
  return (
    <>
      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <SectionHeading>Two cases</SectionHeading>
          <span className="text-small text-text-tertiary">
            Choose a case: every chart below follows it.
          </span>
        </div>
        <CaseCards cases={run.cases} chosen={chosen} onChoose={setChosen} />
      </section>
      <DriversCard data={page.drivers} chosen={chosen} />
      <div className={pairGrid(Math.max(page.interestCover.head.length, page.ebitda.head.length))}>
        <CoverCard
          data={page.interestCover}
          periods={page.periods}
          cases={run.cases}
          chosen={chosen}
        />
        <PathsCard data={page.ebitda} periods={page.periods} />
      </div>
      <section className="flex flex-col gap-4">
        <SectionHeading>Cash flow in FY26</SectionHeading>
        <div className={pairGrid(page.walk.head.length)}>
          <WalkCard data={page.walk} chosen={chosen} />
          <div className="flex min-w-0 flex-col gap-6">
            <GapPanel reason={gapReason(page.gap)} />
            <Passage
              tone="info"
              title={page.watch.title}
              trace={
                page.watch.trace === null ? undefined : (
                  <TraceControl
                    href={page.watch.trace}
                    label={`Show the sources for ${page.watch.title}`}
                  />
                )
              }
            >
              {page.watch.text}
            </Passage>
            <Item
              title={page.limitations.title}
              text={page.limitations.text}
              href={page.limitations.href}
              trace={null}
            />
          </div>
        </div>
      </section>
    </>
  );
}

export function ForecastPage({ params }: { params: Record<string, string> }) {
  return (
    <RunPage params={params} current="forecast">
      {(run) => <Body key={runKey(run)} run={run} />}
    </RunPage>
  );
}
