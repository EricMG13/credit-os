// After the shadcnblocks List Panel, Stacked variant, with a number in the item's media slot (mock
// departure 8: the Numbered variant is behind the source's paid tier, so the marker is drawn here).
// The number is the item's place in the list, as an ordered list shows it.
export function NumberedPanel({ items }: { items: string[] }) {
  return (
    <ol className="overflow-hidden rounded-md border border-border-hairline bg-surface-card">
      {items.map((item, index) => (
        <li
          key={item}
          className="flex items-start gap-4 p-4 not-first:border-t not-first:border-border-hairline"
        >
          <span
            aria-hidden="true"
            className="grid size-8 shrink-0 place-items-center rounded-xs border border-border-hairline bg-surface-subtle text-sm font-semibold text-text-primary tabular-nums"
          >
            {String(index + 1)}
          </span>
          <span className="text-sm font-medium text-text-primary">{item}</span>
        </li>
      ))}
    </ol>
  );
}
