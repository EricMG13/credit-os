// One bar per week (mock `.sp`: 96px wide, 40px tall, 3px between slots, 2px corners, the action
// colour). A week with a reading draws a bar whose height is the delivered 0 to 1 (position only);
// a reading of zero draws a 2px stub; a week with no reading leaves its slot empty. The group is
// one image whose text alternative gives each week's label and delivered count.
import type { SignalSourceWeek } from "../slice";

function Slot({ week }: { week: SignalSourceWeek }) {
  // The reader accepts a count and a height together or neither, so either null is no reading.
  const { items, height } = week;
  if (items === null || height === null) {
    return <span data-week-state="empty" className="flex h-full flex-1 items-end" />;
  }
  return (
    <span
      data-week-state={height === 0 ? "zero" : "value"}
      className="flex h-full flex-1 items-end"
    >
      {height === 0 ? (
        <span className="block h-0.5 w-full rounded-[2px] bg-brand-solid" />
      ) : (
        <span
          className="block w-full rounded-[2px] bg-brand-solid"
          style={{ height: `${String(height * 100)}%` }}
        />
      )}
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
