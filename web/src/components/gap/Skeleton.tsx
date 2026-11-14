/** Static blocks in the shape of what will arrive; the last line is shorter. */
export function Skeleton({ lines }: { lines: number }) {
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
