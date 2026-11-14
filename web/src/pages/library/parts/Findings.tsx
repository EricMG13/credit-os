import type { Finding } from "../slice";
import { TRACE_HOST, TraceControl } from "./TraceControl";

/**
 * The numbered list of key findings (P2): the delivered number, a 600-weight lead and the body, in
 * the system's 16 / 26 body, with one trace control per finding.
 */
export function Findings({ findings }: { findings: readonly Finding[] }) {
  return (
    <ol className="flex flex-col gap-2.5">
      {findings.map((finding) => (
        <li
          key={finding.number}
          className={`${TRACE_HOST} flex items-start gap-4 rounded-lg border border-border-hairline bg-surface-card p-4 text-body`}
        >
          <span
            aria-hidden="true"
            className="w-6.5 flex-none font-medium text-text-tertiary tabular-nums"
          >
            {finding.number}
          </span>
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <span className="text-body font-semibold text-text-primary">{finding.lead}</span>
            <span className="max-w-[72ch] text-body text-text-secondary">{finding.body}</span>
          </div>
          <TraceControl trace={finding.trace} label="Show sources for this finding" />
        </li>
      ))}
    </ol>
  );
}
