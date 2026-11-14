// After sources/uui/tags.tsx, plain and non-interactive: a story's topic tags, as drawn.
export function Tags({ tags }: { tags: string[] }) {
  return (
    <ul className="flex flex-wrap items-center gap-2">
      {tags.map((tag) => (
        <li
          key={tag}
          className="rounded-md bg-surface-card px-2 py-[3px] text-xs font-medium text-text-secondary ring-1 ring-border-hairline ring-inset"
        >
          {tag}
        </li>
      ))}
    </ul>
  );
}
