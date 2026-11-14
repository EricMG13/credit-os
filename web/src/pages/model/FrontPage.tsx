import { Card } from "@/components/card/Card";
import { Banner } from "./parts/Banner";
import { DetailsList } from "./parts/DetailsList";
import { Item } from "./parts/Item";
import { MetricTile } from "./parts/MetricTile";
import { RunPage } from "./parts/RunPage";
import { TraceControl } from "./parts/TraceControl";

const SECTION_TITLE = "font-display text-h3 text-text-primary";

export function FrontPage({ params }: { params: Record<string, string> }) {
  return (
    <RunPage params={params} current="front">
      {({ front, issuer, run }) => (
        <>
          <section aria-label="Bottom line">
            <Banner
              lead={front.bottomLine.lead}
              trace={
                front.bottomLine.trace === null ? null : (
                  <TraceControl
                    href={front.bottomLine.trace}
                    label="Show the sources for the bottom line"
                    onInverse
                  />
                )
              }
            >
              {front.bottomLine.rest}
            </Banner>
          </section>
          <section className="flex flex-col gap-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className={SECTION_TITLE}>Headline figures</h2>
              <span className="text-small text-text-tertiary">{front.headline.period}</span>
            </div>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-6">
              {front.headline.metrics.map((metric, index) => (
                <MetricTile key={index} metric={metric} />
              ))}
            </div>
          </section>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(360px,1fr))] gap-6">
            <section className="flex flex-col gap-4">
              <h2 className={SECTION_TITLE}>What the model covers</h2>
              <Card>
                <DetailsList
                  rows={front.covers.facts.map((fact) => ({
                    term: fact.label,
                    detail: fact.value,
                    trace:
                      fact.trace === null ? null : (
                        <TraceControl
                          href={fact.trace}
                          label={`Show the sources for ${fact.label}`}
                        />
                      ),
                  }))}
                />
              </Card>
            </section>
            <section className="flex flex-col gap-4">
              <h2 className={SECTION_TITLE}>Parts of the model</h2>
              <div className="flex flex-col gap-2">
                {front.parts.map((part, index) => (
                  <Item
                    key={index}
                    title={part.title}
                    text={part.text}
                    href={
                      part.to === null
                        ? null
                        : `#/model/${encodeURIComponent(issuer)}/${encodeURIComponent(run)}/${part.to}`
                    }
                    trace={
                      part.trace === null ? null : (
                        <TraceControl
                          href={part.trace}
                          label={`Show the sources for ${part.title}`}
                        />
                      )
                    }
                  />
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </RunPage>
  );
}
