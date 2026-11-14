import { useId, type ReactNode } from "react";

/** A card holds a group of source components or a chart; it is a named group when it has a title. */
export function Card({ title, children }: { title?: string; children: ReactNode }) {
  const titleId = useId();
  const classes =
    "rounded-ds-lg border border-border-subtle bg-surface-card p-8 shadow-1 text-text-primary";
  if (title === undefined) return <div className={classes}>{children}</div>;
  return (
    <div role="group" aria-labelledby={titleId} className={classes}>
      <h3 id={titleId} className="mb-4 font-display text-h3 text-text-primary">
        {title}
      </h3>
      {children}
    </div>
  );
}

/** A tile is a smaller, flat container: no shadow. */
export function Tile({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-ds-md border border-border-subtle bg-surface-card p-6 text-text-primary">
      {children}
    </div>
  );
}
