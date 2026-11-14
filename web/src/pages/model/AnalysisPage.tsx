import type { ReactNode } from "react";
import { ArrowUpRight } from "@untitledui/icons";
import { Card } from "@/components/card/Card";
import { Collapsible } from "./parts/Collapsible";
import { Passage } from "./parts/Passage";
import { ListPanel } from "./parts/ListPanel";
import { RunPage, runKey } from "./parts/RunPage";
import { SectionIndex, type SectionEntry } from "./parts/SectionIndex";
import { Stat } from "./parts/Stat";
import { TraceControl } from "./parts/TraceControl";
import { HeadroomSection, JUMP_TARGET, SegmentsSection } from "./sections/AnalysisCharts";
import type { AnalysisPage as Analysis } from "./slice/types";

const ID = {
  findings: "analysis-key-findings",
  measures: "analysis-measures",
  headroom: "analysis-headroom",
  segments: "analysis-segment-margins",
  contrary: "analysis-contrary-evidence",
  watch: "analysis-what-would-change-the-view",
  limitations: "analysis-limitations",
} as const;

const ENTRIES: SectionEntry[] = [
  { id: ID.findings, label: "Key findings" },
  { id: ID.measures, label: "Measures" },
  { id: ID.headroom, label: "Headroom" },
  { id: ID.segments, label: "Segment margins" },
  { id: ID.contrary, label: "Contrary evidence" },
  { id: ID.watch, label: "What would change the view" },
  { id: ID.limitations, label: "Limitations" },
];

/** A section heading the index can move focus to. */
function Heading({ id, children }: { id: string; children: string }) {
  return (
    <h2 id={id} tabIndex={-1} className={`font-display text-h3 text-text-primary ${JUMP_TARGET}`}>
      {children}
    </h2>
  );
}

function traceFor(trace: string | null, title: string): ReactNode {
  return trace === null ? null : (
    <TraceControl href={trace} label={`Show the sources for ${title}`} />
  );
}

function Body({ page }: { page: Analysis }) {
  const { limitations } = page;
  return (
    <div className="flex flex-col gap-8 min-[900px]:flex-row min-[900px]:gap-10">
      <SectionIndex entries={ENTRIES} />
      <div className="flex min-w-0 flex-1 flex-col gap-16">
        <section className="flex flex-col gap-6">
          <Heading id={ID.findings}>Key findings</Heading>
          <ListPanel
            label="Key findings"
            items={page.findings.map((f) => ({
              number: f.number,
              lead: f.title,
              text: f.text,
              trace: traceFor(f.trace, f.title),
            }))}
          />
        </section>
        <section className="flex flex-col gap-6">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <Heading id={ID.measures}>Measures and what they mean</Heading>
            <span className="text-small text-text-tertiary">{page.measures.period}</span>
          </div>
          <Card>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,280px),1fr))] gap-x-10 gap-y-8">
              {page.measures.stats.map((stat) => (
                <Stat
                  key={stat.label}
                  label={stat.label}
                  value={stat.value}
                  delta={stat.delta}
                  text={stat.text}
                  trace={traceFor(stat.trace, stat.label)}
                />
              ))}
            </div>
          </Card>
        </section>
        <HeadroomSection id={ID.headroom} data={page.headroom} />
        <SegmentsSection id={ID.segments} data={page.segments} />
        <section className="flex flex-col gap-6">
          <Heading id={ID.contrary}>Contrary evidence</Heading>
          <Passage
            tone="warning"
            title={page.contrary.title}
            trace={traceFor(page.contrary.trace, page.contrary.title)}
          >
            {page.contrary.text}
          </Passage>
        </section>
        <section className="flex flex-col gap-6">
          <Heading id={ID.watch}>What would change the view</Heading>
          <Passage
            tone="info"
            title={page.watch.title}
            trace={traceFor(page.watch.trace, page.watch.title)}
          >
            {page.watch.text}
          </Passage>
        </section>
        <section className="flex flex-col gap-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Heading id={ID.limitations}>Limitations</Heading>
              <span className="rounded-full border border-border-hairline bg-surface-subtle px-2 text-caption text-text-secondary">
                {limitations.count}
              </span>
            </div>
            <a
              href={limitations.href}
              className="inline-flex items-center gap-1 text-small text-text-link"
            >
              {limitations.linkText}
              <ArrowUpRight className="size-4" aria-hidden="true" />
            </a>
          </div>
          <div className="flex flex-col gap-3">
            {limitations.items.map((item) => (
              <Collapsible key={item.title} summary={item.title}>
                <p className="group/trace flex items-start gap-3 break-words">
                  <span className="min-w-0 flex-1 break-words">{item.text}</span>
                  {traceFor(item.trace, item.title)}
                </p>
              </Collapsible>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

export function AnalysisPage({ params }: { params: Record<string, string> }) {
  return (
    <RunPage params={params} current="analysis">
      {(run) => <Body key={runKey(run)} page={run.analysis} />}
    </RunPage>
  );
}
