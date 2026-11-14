// One bar per week (mock `.sp`: 96px wide, 40px tall, 3px between slots, 2px corners, the action
// colour). A week with a reading draws a bar whose height is the delivered 0 to 1 (position only);
// a reading of zero draws a 2px stub; a week with no reading leaves its slot empty. The group is
// one image whose text alternative gives each week's label and delivered count.
import type { SignalSourceWeek } from "../slice";

function Slot({ week }: { week: SignalSourceWeek }) {
  const state = week.items === null ? "empty" : week.height === 0 ? "zero" : "value";
  return (
    <span data-week-state={state} className="flex h-full flex-1 items-end">
      {state === "zero" ? (
        <span className="block h-0.5 w-full rounded-[2px] bg-brand-solid" />
      ) : null}
      {state === "value" ? (
        <span
          className="block w-full rounded-[2px] bg-brand-solid"
          style={{ height: `${String((week.height ?? 0) * 100)}%` }}
        />
      ) : null}
    </span>
  );
}

export function WeekBars({ weeks }: { weeks: SignalSourceWeek[] }) {
  const text = weeks.map((w) => `${w.label}: ${w.items ?? "no reading"}`).join("; ");
  return (
    <span
      role="img"
      aria-label={`Items per week. ${text}`}
      className="inline-flex h-10 w-24 items-end gap-[3px] py-[5px]"
    >
      {weeks.map((w, i) => (
        <Slot key={`${String(i)}:${w.label}`} week={w} />
      ))}
    </span>
  );
}
