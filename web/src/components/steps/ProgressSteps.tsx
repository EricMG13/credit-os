// Follows HyperUI "Steps: timeline with title, with highlighted current step" (steps-5).
import { cx } from "@/utils/cx";

type StepState = "complete" | "current" | "incomplete";

interface Step {
  title: string;
  state: StepState;
}

const STATE_WORD: Record<StepState, string> = {
  complete: "complete",
  current: "current",
  incomplete: "not started",
};

/** The source's check mark, drawn as inline SVG for a complete step. */
function Check() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="size-3.5"
    >
      <path d="M4.5 10.5l3.5 3.5 7.5-8" />
    </svg>
  );
}

/** A horizontal ordered list of steps. Each state has a marker and a word, not colour alone. */
export function ProgressSteps({ steps }: { steps: Step[] }) {
  return (
    <div className="relative after:absolute after:inset-x-0 after:top-1/2 after:block after:h-0.5 after:-translate-y-1/2 after:rounded-lg after:bg-border-hairline">
      <ol className="relative z-10 flex justify-between text-sm font-medium text-text-secondary">
        {steps.map((step, index) => (
          <li
            key={step.title}
            aria-current={step.state === "current" ? "step" : undefined}
            className="flex items-center gap-2 bg-surface-card p-2"
          >
            <span
              aria-hidden="true"
              className={cx(
                "flex size-6 items-center justify-center rounded-full text-center text-[10px]/6 font-bold",
                step.state === "incomplete" ? "bg-surface-subtle" : "bg-action text-text-on-action",
              )}
            >
              {step.state === "complete" ? <Check /> : index + 1}
            </span>
            <span className={cx("max-sm:sr-only", step.state === "current" && "text-text-primary")}>
              {step.title}
            </span>
            <span className="sr-only">{`, ${STATE_WORD[step.state]}`}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
