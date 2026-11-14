import { Check } from "@untitledui/icons";
import { cx } from "@/utils/cx";

const STEPS = [
  { key: "documents", title: "Documents", note: "Add files" },
  { key: "purpose", title: "Purpose", note: "Choose one" },
  { key: "confirm", title: "Confirm", note: "Approve" },
  { key: "context", title: "More context", note: "Optional" },
  { key: "start", title: "Start", note: "Paid step" },
] as const;

/** The five steps of a run start. A step before `step` is complete; on any other step key (the
 *  started draft) all five are. Each state is said in words as well as drawn. */
export function Stepper({ step }: { step: string }) {
  const at = STEPS.findIndex((s) => s.key === step);
  const current = at === -1 ? STEPS.length : at;
  return (
    <ol aria-label="Steps in this run" className="flex flex-wrap items-center gap-x-4 gap-y-3">
      {STEPS.map((s, i) => {
        const done = i < current;
        return (
          <li
            key={s.key}
            aria-current={i === current ? "step" : undefined}
            className="flex min-w-0 flex-1 items-center gap-4 last:flex-none"
          >
            <span className="inline-flex items-center gap-3">
              <span
                aria-hidden="true"
                className={cx(
                  "flex size-7 shrink-0 items-center justify-center rounded-full border-2 text-sm font-medium",
                  i <= current
                    ? "border-action bg-action text-text-on-action"
                    : "border-border-hairline bg-surface-card text-text-tertiary",
                )}
              >
                {done ? <Check className="size-4" /> : i + 1}
              </span>
              <span className="flex flex-col">
                <span className="text-sm font-medium text-text-primary">{s.title}</span>
                <span className="text-xs text-text-tertiary">{s.note}</span>
                <span className="sr-only">
                  {done ? "Complete" : i === current ? "Current step" : "Not started"}
                </span>
              </span>
            </span>
            {i < STEPS.length - 1 ? (
              <span
                aria-hidden="true"
                className={cx("h-px min-w-3 flex-1", done ? "bg-action" : "bg-border-hairline")}
              />
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
