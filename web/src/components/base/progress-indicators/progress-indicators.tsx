import { useId } from "react";
import { cx } from "@/utils/cx";

export interface ProgressBarProps {
  /** The current value; sets the fill's position only. */
  value: number;
  /** The total the value counts toward (greater than 0). */
  max: number;
  /** The text shown beside the bar, for example "3 of 8", supplied by the caller. */
  label: string;
  className?: string;
}

/** The source's bar with its label at the right. The label is the caller's text; nothing is computed for display. */
export const ProgressBar = ({ value, max, label, className }: ProgressBarProps) => {
  const labelId = useId();
  if (!(max > 0)) throw new RangeError("ProgressBar needs a max greater than 0");
  const percentage = Math.min(100, Math.max(0, (value * 100) / max));

  return (
    <div className="flex items-center gap-3">
      <div
        role="progressbar"
        aria-labelledby={labelId}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        className={cx("h-2 w-full overflow-hidden rounded-md bg-action-subtle", className)}
      >
        <div
          // Use transform instead of width to avoid layout thrashing (and for smoother animation)
          style={{ transform: `translateX(-${String(100 - percentage)}%)` }}
          className="size-full rounded-md bg-action transition-transform duration-200 ease-[cubic-bezier(.2,0,0,1)]"
        />
      </div>
      <span id={labelId} className="shrink-0 text-sm font-medium text-secondary tabular-nums">
        {label}
      </span>
    </div>
  );
};
