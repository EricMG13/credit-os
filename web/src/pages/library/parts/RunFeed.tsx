import { Link } from "react-aria-components";
import { Badge } from "@/components/base/badges/badges";
import { StatusBadge } from "@/components/status/StatusBadge";
import { STATUS_SETS, type Tone } from "@/components/status/sets";
import { StatusShape } from "@/components/status/shapes";
import type { History } from "../slice";
import { TEXT_LINK, changesHref, overviewHref } from "./links";

/** The marker disc takes the state's tone; the shape inside says the state without the colour. */
const MARKER: Record<Tone, string> = {
  success: "bg-success-fill text-success-mark",
  warning: "bg-warning-fill text-warning-mark",
  error: "bg-error-fill text-error-mark",
  info: "bg-info-fill text-info-mark",
  action: "bg-action-subtle text-action",
  neutral: "bg-surface-subtle text-text-secondary",
  gap: "bg-surface-subtle text-text-secondary",
};

const LINK = `${TEXT_LINK} text-body font-semibold text-action underline`;

/** One entry per run, newest first as delivered, joined by a dotted line down the marker rail. */
export function RunFeed({ issuer, history }: { issuer: string; history: History }) {
  return (
    <ol className="flex max-w-180 flex-col">
      {history.entries.map((entry, index) => {
        const { shape, tone } = STATUS_SETS["Run states"][entry.state];
        const last = index === history.entries.length - 1;
        return (
          <li
            key={`${entry.asOf}-${entry.ran}`}
            className={`relative flex gap-3 ${last ? "" : "pb-8"}`}
          >
            <div className="flex w-10 flex-none flex-col items-center gap-1">
              <span
                className={`flex size-10 flex-none items-center justify-center rounded-ds-full ${MARKER[tone]}`}
              >
                <StatusShape shape={shape} />
              </span>
              {last ? null : (
                <span className="-mb-7 w-0 flex-1 border-l-[2.4px] border-dotted border-connector" />
              )}
            </div>
            <div className="flex min-w-0 flex-1 flex-col gap-1.5 pt-0.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-lg font-medium text-text-primary">{`Run as of ${entry.asOf}`}</span>
                <span className="text-xs text-text-tertiary">{`Ran ${entry.ran}`}</span>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge set="Run states" state={entry.state} />
                <Badge size="sm">{entry.pathway}</Badge>
              </div>
              <p className="max-w-[64ch] text-body text-text-tertiary">{entry.text}</p>
              {entry.report === null ? null : (
                <div className="flex flex-wrap gap-4">
                  <Link href={overviewHref(issuer, entry.report)} className={LINK}>
                    Open report
                  </Link>
                  {entry.changes === null ? null : (
                    <Link href={changesHref(issuer, entry.changes.run)} className={LINK}>
                      {entry.changes.label}
                    </Link>
                  )}
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
