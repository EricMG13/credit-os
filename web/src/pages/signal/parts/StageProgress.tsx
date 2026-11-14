// After sources/hui/progress-bars-2.html (label row and track), with the four stage names under the
// track (mock departure 7). The label is delivered ("Stage 3 of 4"); `position` only places the fill,
// so no percentage is computed or shown as text. Nothing here animates.
import type { SignalStory } from "../slice";

type Stage = NonNullable<SignalStory["stage"]>;

export function StageProgress({ stage }: { stage: Stage }) {
  return (
    <div className="mt-3 max-w-[440px]">
      <div className="flex justify-between gap-4 text-sm font-medium text-text-primary">
        <span>{stage.current}</span>
        <span>{stage.label}</span>
      </div>
      <div
        role="progressbar"
        aria-label="Case stage"
        aria-valuemin={0}
        aria-valuemax={1}
        aria-valuenow={stage.position}
        aria-valuetext={`${stage.label}: ${stage.current}`}
        className="mt-2 h-2 overflow-hidden rounded-full bg-action-subtle"
      >
        <div
          className="h-full rounded-full bg-action"
          style={{ width: `${String(stage.position * 100)}%` }}
        />
      </div>
      <ol className="mt-1.5 flex justify-between gap-2 text-sm text-text-tertiary">
        {stage.stages.map((s, index) => (
          <li
            key={index}
            aria-current={s.current ? "step" : undefined}
            className={s.current ? "font-semibold text-text-primary" : undefined}
          >
            {s.name}
          </li>
        ))}
      </ol>
    </div>
  );
}
