// The new-stories pill (mock `.pill`, departure 17): white with a hairline edge, a status dot, the
// delivered label and one action. The dot is decoration; the words carry the meaning.
export function Pill({
  label,
  action,
  onAction,
}: {
  label: string;
  action: string;
  onAction: () => void;
}) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-border-hairline bg-surface-card px-3 py-1.5 text-xs text-text-primary">
      <span aria-hidden="true" className="size-2 rounded-full bg-current text-info-mark" />
      <b className="border-r border-border-hairline pr-2 font-medium">{label}</b>
      <button
        type="button"
        aria-label={`${action} ${label}`}
        onClick={onAction}
        className="cursor-pointer rounded-full outline-focus-ring hover:underline focus-visible:outline-2"
      >
        {action}
      </button>
    </span>
  );
}
