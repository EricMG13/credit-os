import { Missing } from "@/components/gap/Missing";
import type { Row } from "../slice";

// Kit candidate: HyperUI details list (dl, two columns here, 12px rows, 1px dividers).
// A null value draws the kit's Missing.
export function DetailsList({ rows }: { rows: Row[] }) {
  return (
    <dl className="text-sm">
      {rows.map((row, i) => (
        <div
          key={`${String(i)}-${row.label}`}
          className="grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)] gap-4 border-t border-border-subtle py-3 first:border-t-0"
        >
          <dt className="font-medium text-text-primary">{row.label}</dt>
          <dd className="wrap-anywhere text-text-secondary">
            {row.value === null ? <Missing /> : row.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
