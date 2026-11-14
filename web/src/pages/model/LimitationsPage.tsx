import { ArrowUpRight } from "@untitledui/icons";
import { Badge } from "@/components/base/badges/badges";
import { GapPanel } from "@/components/gap/GapPanel";
import { Collapsible } from "./parts/Collapsible";
import { RunPage } from "./parts/RunPage";
import { TraceControl } from "./parts/TraceControl";

/** GapPanel draws its own fixed title; until it takes one, the gap's title leads its reason. */
function gapReason(title: string, reason: string): string {
  return `${title}. ${reason}`;
}

export function LimitationsPage({ params }: { params: Record<string, string> }) {
  return (
    <RunPage params={params} current="limitations">
      {({ limitations, links }) => (
        <>
          <section className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <h2 className="font-display text-h3 text-text-primary">Limitations</h2>
                <span className="rounded-full border border-border-hairline bg-surface-subtle px-2 text-caption text-text-secondary">
                  {limitations.count}
                </span>
              </div>
              <a
                href={links.evidenceGaps}
                className="inline-flex items-center gap-1 text-small text-text-link"
              >
                {limitations.gapsLinkText}
                <ArrowUpRight className="size-4" aria-hidden="true" />
              </a>
            </div>
            <p className="max-w-[72ch] text-body text-text-secondary">{limitations.lead}</p>
            <div className="flex flex-col gap-3">
              {limitations.items.map((item, index) => (
                <Collapsible
                  key={index}
                  summary={
                    <>
                      {item.title}
                      <Badge size="sm">{item.label}</Badge>
                    </>
                  }
                >
                  <p className="group/trace flex items-start gap-3 break-words">
                    <span className="min-w-0 flex-1 break-words">{item.text}</span>
                    {item.trace === null ? null : (
                      <TraceControl
                        href={item.trace}
                        label={`Show the sources for ${item.title}`}
                      />
                    )}
                  </p>
                </Collapsible>
              ))}
            </div>
          </section>
          <section className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <h2 className="font-display text-h3 text-text-primary">
                Not established for this run
              </h2>
              <span className="rounded-full border border-border-hairline bg-surface-subtle px-2 text-caption text-text-secondary">
                {limitations.notEstablished.count}
              </span>
            </div>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(300px,1fr))] gap-4">
              {limitations.notEstablished.items.map((gap, index) => (
                <GapPanel key={index} reason={gapReason(gap.title, gap.reason)} />
              ))}
            </div>
          </section>
        </>
      )}
    </RunPage>
  );
}
