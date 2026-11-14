import type { ReactNode } from "react";
import type { Evidence } from "../slice";
import { CopyProvider } from "./CopyToast";
import { RunTabLink } from "./RunFrame";
import { SECTION_HEADING } from "./heading";
import { evidenceHref } from "./links";

export type EvidenceTab = "summary" | "trace" | "sources" | "gaps" | "record";

/**
 * The frame of every Evidence page, inside the run's frame: the heading and its one sentence, the
 * module filter where the page has one, the five tabs with their delivered counts, and the page. The
 * Trace, Gaps and Record tabs lead to pages a later step adds.
 */
export function EvidenceFrame({
  issuer,
  run,
  evidence,
  current,
  filter,
  children,
}: {
  issuer: string;
  run: string;
  evidence: Evidence;
  current: EvidenceTab;
  /** The module filter, drawn at the right of the heading by a page that narrows something. */
  filter?: ReactNode;
  children: ReactNode;
}) {
  const Heading = SECTION_HEADING;
  const tab = (page: EvidenceTab, label: string, count?: string) => (
    <RunTabLink
      href={evidenceHref(issuer, run, page)}
      current={current === page}
      label={label}
      count={count}
      small
    />
  );
  return (
    <CopyProvider>
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Heading className="font-display text-h2 text-text-primary">Evidence</Heading>
            <p className="mt-1 text-text-secondary">{evidence.intro}</p>
          </div>
          {filter}
        </div>
        <nav
          aria-label="Evidence sections"
          className="flex flex-wrap gap-3 border-b border-border-hairline"
        >
          {tab("summary", "Summary")}
          {tab("trace", "Trace", evidence.tabs.trace)}
          {tab("sources", "Sources", evidence.tabs.sources)}
          {tab("gaps", "Gaps", evidence.tabs.gaps)}
          {tab("record", "Record")}
        </nav>
        {children}
      </div>
    </CopyProvider>
  );
}
