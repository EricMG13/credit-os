import { Button } from "@/components/base/buttons/button";
import { ProgressBar } from "@/components/base/progress-indicators/progress-indicators";
import type { Evidence } from "./slice";
import { DownloadButton } from "./parts/DownloadButton";
import { MetricTile } from "./parts/MetricTile";
import { Snippet } from "./parts/Snippet";
import { SUBSECTION_HEADING } from "./parts/heading";
import { evidenceHref } from "./parts/links";

const H = "font-display text-h3 text-text-primary";

/** The Summary tab: modules delivered, the counts, this run's code and hash, and what to take with you. */
export function EvidenceSummary({
  evidence,
  issuer,
  run,
}: {
  evidence: Evidence;
  issuer: string;
  run: string;
}) {
  const Heading = SUBSECTION_HEADING;
  const { delivered, counts, run: code, take } = evidence.summary;
  return (
    <div className="flex flex-col gap-8">
      <section
        aria-labelledby="delivered-heading"
        className="flex flex-col gap-4 rounded-xl border border-border-subtle bg-surface-card p-5 shadow-xs"
      >
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <Heading id="delivered-heading" className="font-display text-h4 text-text-primary">
            Modules delivered
          </Heading>
          {delivered.note === null ? null : (
            <span className="text-small text-text-tertiary">{delivered.note}</span>
          )}
        </div>
        <ProgressBar
          value={delivered.progress.value}
          max={delivered.progress.max}
          label={delivered.progress.text}
        />
      </section>
      <section aria-label="Counts">
        <ul className="grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-4">
          {counts.map((count) => (
            <MetricTile key={count.label} metric={count} />
          ))}
        </ul>
      </section>
      <div className="grid grid-cols-1 gap-6 min-[1200px]:grid-cols-2">
        <section className="flex flex-col gap-4">
          <Heading className={H}>This run</Heading>
          <Snippet
            caption="Run code"
            kind="Code"
            value={code.code}
            copyLabel="Copy run code"
            what="The run code"
          />
          <Snippet
            caption="Hash of the handoff set"
            kind="SHA-256"
            value={code.hash}
            copyLabel="Copy hash"
            what="The hash of the handoff set"
          />
        </section>
        <section className="flex flex-col items-start gap-4">
          <Heading className={H}>Take it with you</Heading>
          <p className="text-text-secondary">{take.text}</p>
          <div className="flex flex-wrap items-center gap-3">
            <DownloadButton download={take.download} />
            <Button href={evidenceHref(issuer, run, "sources")} color="tertiary">
              See which files were used
            </Button>
          </div>
        </section>
      </div>
    </div>
  );
}
