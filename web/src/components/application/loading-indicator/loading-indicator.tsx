interface LoadingIndicatorProps {
  /** Text shown below the spinner; it also names the status for assistive technology. */
  label: string;
}

/** The `line-simple` spinner at the source's `sm` size. It loops, so it belongs to live run state only. */
export const LoadingIndicator = ({ label }: LoadingIndicatorProps) => {
  return (
    <div
      role="status"
      aria-label={label}
      className="flex flex-col items-center justify-center gap-4"
    >
      <svg aria-hidden="true" className="size-8 animate-spin" viewBox="0 0 32 32" fill="none">
        <circle
          className="text-action-subtle"
          cx="16"
          cy="16"
          r="14"
          stroke="currentColor"
          strokeWidth="4"
        />
        <circle
          className="stroke-action"
          cx="16"
          cy="16"
          r="14"
          fill="none"
          strokeWidth="4"
          strokeDashoffset="75"
          strokeDasharray="100"
          strokeLinecap="round"
        />
      </svg>
      <span aria-hidden="true" className="text-sm font-medium text-secondary">
        {label}
      </span>
    </div>
  );
};
