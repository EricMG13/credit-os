import { STATUS_SETS, type Tone } from "@/components/status/sets";
import { StatusShape } from "@/components/status/shapes";
import { cx } from "@/utils/cx";
import type { ActivityLine } from "../slice-activity";
import "./activity.css";

const MARK: Record<Tone, string> = {
  success: "text-success-mark",
  warning: "text-warning-mark",
  error: "text-error-mark",
  info: "text-info-mark",
  neutral: "text-text-tertiary",
  action: "text-action",
  gap: "text-text-tertiary",
};

function stateOf(line: ActivityLine) {
  return line.state === "Not assessable"
    ? STATUS_SETS["Module state"]["Not assessable"]
    : STATUS_SETS["Run states"][line.state];
}

/** The connected activity feed, newest first. In a live run the newest line rises in once. */
export function Feed({ lines, live }: { lines: ActivityLine[]; live: boolean }) {
  return (
    <ul>
      {lines.map((line, i) => {
        const { shape, tone } = stateOf(line);
        const last = i === lines.length - 1;
        return (
          <li key={`${line.time}-${line.who}-${String(i)}`}>
            <article className={cx("flex gap-3", live && i === 0 && "feed-rise")}>
              <div className="flex flex-none flex-col items-center">
                <span
                  className={cx(
                    "flex size-10 shrink-0 items-center justify-center rounded-full bg-surface-subtle",
                    MARK[tone],
                  )}
                >
                  <StatusShape shape={shape} />
                  <span className="sr-only">{line.state}</span>
                </span>
                {last ? null : (
                  <span
                    aria-hidden="true"
                    className="my-1 min-h-3 flex-1 border-s-[3px] border-dotted border-connector"
                  />
                )}
              </div>
              <div className={cx("flex min-w-0 flex-1 flex-col", last ? "pb-0" : "pb-8")}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-text-secondary">{line.who}</span>
                  <time className="text-xs text-text-tertiary tabular-nums">{line.time}</time>
                </div>
                <p className="text-sm text-pretty text-text-tertiary">{line.text}</p>
              </div>
            </article>
          </li>
        );
      })}
    </ul>
  );
}
