import type { ReactNode } from "react";

/** A details list: one `dl`, each row a term and its definition with room for a trace control. */
export function DetailsList({
  rows,
}: {
  rows: readonly { term: string; detail: string; trace: ReactNode }[];
}) {
  return (
    <dl className="m-0 text-body">
      {rows.map((row, index) => (
        <div
          key={index}
          className="group/trace grid grid-cols-[1fr_2fr] gap-4 border-t border-border-hairline py-3 first:border-t-0 first:pt-0 last:pb-0"
        >
          <dt className="font-medium text-text-primary">{row.term}</dt>
          <dd className="m-0 flex items-start justify-between gap-2 text-text-secondary">
            <span className="min-w-0 break-words">{row.detail}</span>
            {row.trace}
          </dd>
        </div>
      ))}
    </dl>
  );
}
