import { StatusShape } from "@/components/status/shapes";
import { STATUS_SETS } from "@/components/status/sets";
import { TextLink } from "../TextLink";
import type { RunRecord } from "../slice-activity";

type Alert = NonNullable<RunRecord["alert"]>;

const MARK = {
  error: "text-error-mark",
  warning: "text-warning-mark",
  neutral: "text-text-secondary",
} as const;

/**
 * The alert of an ended run, marked with the run state's own shape. Failed says "alert";
 * the others say "status". The state's word is read out before the title.
 */
export function RunAlert({ state, alert }: { state: RunRecord["state"]; alert: Alert }) {
  const { shape, tone, word } = STATUS_SETS["Run states"][state];
  return (
    <div
      role={state === "Failed" ? "alert" : "status"}
      className="flex items-start gap-4 rounded-ds-lg border border-border-container bg-surface-card p-4 shadow-xs"
    >
      <span
        className={`flex size-6 flex-none items-center justify-center ${
          tone === "error" || tone === "warning" ? MARK[tone] : MARK.neutral
        }`}
      >
        <StatusShape shape={shape} />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <div className="flex flex-col gap-1">
          <p className="text-sm font-semibold text-text-secondary">
            <span className="sr-only">{word}: </span>
            {alert.title}
          </p>
          <p className="text-sm text-pretty text-text-tertiary">{alert.text}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <TextLink href={alert.action.href}>{alert.action.label}</TextLink>
          {alert.alt === null ? null : <TextLink href={alert.alt.href}>{alert.alt.label}</TextLink>}
        </div>
      </div>
    </div>
  );
}
