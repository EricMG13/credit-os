import { Check } from "@untitledui/icons";
import { StatusBadge } from "@/components/status/StatusBadge";
import { cx } from "@/utils/cx";
import type { ModuleStep, ModuleWord } from "../slice-activity";

function ModuleBadge({ word, live }: { word: ModuleWord; live: boolean }) {
  if (word === "Not assessable" || word === "Not run") {
    return <StatusBadge set="Module state" state={word} />;
  }
  return <StatusBadge set="Run states" state={word} live={live} />;
}

function Marker({ word }: { word: ModuleWord }) {
  return (
    <span
      aria-hidden="true"
      className={cx(
        "z-10 flex size-6 shrink-0 items-center justify-center rounded-full",
        word === "Finished" && "bg-action text-text-on-action",
        word === "Running" &&
          "bg-action shadow-[0_0_0_2px_var(--color-surface-card),0_0_0_4px_var(--color-action)]",
        word !== "Finished" &&
          word !== "Running" &&
          "bg-surface-card inset-ring-[1.5px] inset-ring-border-container",
      )}
    >
      {word === "Finished" ? (
        <Check className="size-4" />
      ) : (
        <span
          className={cx(
            "size-2 rounded-full",
            word === "Running" ? "bg-text-on-action" : "bg-text-disabled",
          )}
        />
      )}
    </span>
  );
}

/** Vertical progress steps, one per module, each with its state as a trailing badge. */
export function ModuleSteps({ steps, live }: { steps: ModuleStep[]; live: boolean }) {
  return (
    <ol aria-label="Modules in this run">
      {steps.map((step, i) => {
        const last = i === steps.length - 1;
        const name = step.kind === "module" ? step.name : step.title;
        const detail = step.kind === "module" ? step.detail : null;
        const waiting = live && step.state === "Queued";
        return (
          <li
            key={`${name}-${String(i)}`}
            aria-current={step.state === "Running" ? "step" : undefined}
            className="flex items-start gap-3"
          >
            <div className="flex flex-none flex-col items-center self-stretch">
              <Marker word={step.state} />
              <span
                aria-hidden="true"
                className={cx(
                  "my-1 min-h-3 flex-1 rounded-xs border-s-2",
                  last && "border-transparent",
                  !last && step.state === "Finished" && "border-action",
                  !last && step.state !== "Finished" && "border-border-hairline",
                )}
              />
            </div>
            <div
              className={cx(
                "flex min-w-0 flex-1 items-start justify-between gap-3 pt-0.5",
                last ? "pb-0" : "pb-6",
              )}
            >
              <div className="flex min-w-0 flex-1 flex-col">
                <span
                  className={cx(
                    "text-sm font-semibold",
                    step.state === "Running" ? "text-action" : "text-text-secondary",
                  )}
                >
                  {name}
                </span>
                {detail === null ? null : (
                  <span className="text-sm text-pretty text-text-tertiary">{detail}</span>
                )}
                {waiting ? (
                  <div aria-hidden="true" className="flex max-w-80 flex-col gap-1.5 pt-1.5">
                    <div className="activity-skel queued-shimmer w-[90%]" />
                    <div className="activity-skel queued-shimmer w-[60%]" />
                  </div>
                ) : null}
              </div>
              <ModuleBadge word={step.state} live={live} />
            </div>
          </li>
        );
      })}
    </ol>
  );
}
