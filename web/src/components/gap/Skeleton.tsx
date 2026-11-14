/** Static blocks in the shape of what will arrive; the last line is shorter. */
export function Skeleton({ lines }: { lines: number }) {
  if (!Number.isInteger(lines) || lines < 0) {
    throw new RangeError(`Skeleton lines must be a non-negative integer, got ${String(lines)}`);
  }
  return (
    <div aria-hidden="true" className="flex flex-col gap-2">
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className={`h-4 rounded-ds-xs bg-surface-subtle ${i === lines - 1 && lines > 1 ? "w-2/3" : "w-full"}`}
        />
      ))}
    </div>
  );
}
