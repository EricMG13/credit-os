import { cx } from "@/utils/cx";
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

// The mock's featured-outline mark: two rings round the shape, at 0.3 and 0.1 opacity.
const RINGS =
  "relative m-2.5 flex size-5 flex-none items-center justify-center before:absolute before:top-1/2 before:left-1/2 before:size-7 before:-translate-x-1/2 before:-translate-y-1/2 before:rounded-full before:border-2 before:border-current before:opacity-30 before:content-[''] after:absolute after:top-1/2 after:left-1/2 after:size-[38px] after:-translate-x-1/2 after:-translate-y-1/2 after:rounded-full after:border-2 after:border-current after:opacity-10 after:content-['']";

/**
 * The alert of an ended run, marked with the run state's own shape. Failed says "alert";
 * the others say "status". The state's word is read out before the title.
 */
export function RunAlert({
  state,
  alert,
}: {
  state: RunRecord["state"] | "unreadable";
  alert: Alert;
}) {
  // A record that cannot be read has no run state to name: it is an error, drawn as Failed's diamond.
  const { shape, tone, word } =
    state === "unreadable"
      ? { ...STATUS_SETS["Run states"].Failed, word: "Error" }
      : STATUS_SETS["Run states"][state];
  return (
    <div
      role={state === "Failed" || state === "unreadable" ? "alert" : "status"}
      className="flex items-start gap-4 rounded-ds-lg border border-border-container bg-surface-card p-4 shadow-xs"
    >
      <span
        className={cx(RINGS, tone === "error" || tone === "warning" ? MARK[tone] : MARK.neutral)}
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
          {alert.alt === null ? null : (
            <TextLink href={alert.alt.href} grey>
              {alert.alt.label}
            </TextLink>
          )}
        </div>
      </div>
    </div>
  );
}
