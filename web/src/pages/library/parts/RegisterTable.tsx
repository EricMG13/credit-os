import { useState, type ReactNode } from "react";
import { ArrowDown, ChevronSelectorVertical } from "@untitledui/icons";
import { Badge } from "@/components/base/badges/badges";
import { cx } from "@/utils/cx";
import { SUBSECTION_HEADING } from "./heading";

/** The column a register is sorted by and which way; `null` is the order it was delivered in. */
export type Sort<C extends string = string> = {
  column: C;
  direction: "ascending" | "descending";
} | null;

/** What a row is ordered by in one column: a delivered number or string, `null` when it has none. */
export type SortKey = string | number | null;

/** Sort state, in memory: a column's first press sorts it ascending, the next descending, then ascending again. */
export function useSort<C extends string>(): [Sort<C>, (column: C) => void] {
  const [sort, setSort] = useState<Sort<C>>(null);
  return [
    sort,
    (column) => {
      setSort((now) => ({
        column,
        direction:
          now?.column === column && now.direction === "ascending" ? "descending" : "ascending",
      }));
    },
  ];
}

/** Orders by the delivered keys only; a row with no key goes last whichever way the column runs. */
export function sortRows<T, C extends string>(
  rows: readonly T[],
  sort: Sort<C>,
  keyOf: (row: T, column: C) => SortKey,
): T[] {
  if (sort === null) return [...rows];
  const way = sort.direction === "ascending" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const x = keyOf(a, sort.column);
    const y = keyOf(b, sort.column);
    if (x === null || y === null) return Number(x === null) - Number(y === null);
    if (x === y) return 0;
    return x < y ? -way : way;
  });
}

const HEAD =
  "bg-surface-subtle px-5 py-2 text-left text-xs font-semibold whitespace-nowrap text-quaternary";

/** A column head with no sort. */
export function PlainHead({
  children,
  srOnly = false,
  align = "left",
}: {
  children: string;
  srOnly?: boolean;
  align?: "left" | "right";
}) {
  return (
    <th scope="col" className={cx(HEAD, align === "right" && "text-right")}>
      {srOnly ? <span className="sr-only">{children}</span> : children}
    </th>
  );
}

/** A sortable column head: a button that sorts, with the state in `aria-sort`. */
export function SortHead<C extends string>({
  column,
  label,
  sort,
  onSort,
}: {
  column: C;
  label: string;
  sort: Sort<C>;
  onSort: (column: C) => void;
}) {
  const here = sort?.column === column ? sort.direction : null;
  return (
    <th scope="col" aria-sort={here ?? "none"} className={HEAD}>
      <button
        type="button"
        onClick={() => {
          onSort(column);
        }}
        className="flex items-center gap-1 rounded-ds-xs outline-hidden focus-visible:ring-2 focus-visible:ring-brand"
      >
        {label}
        {here === null ? (
          <ChevronSelectorVertical
            aria-hidden="true"
            size={12}
            strokeWidth={3}
            className="text-fg-quaternary"
          />
        ) : (
          <ArrowDown
            aria-hidden="true"
            className={cx(
              "size-3 stroke-[3px] text-fg-quaternary",
              here === "ascending" && "rotate-180",
            )}
          />
        )}
      </button>
    </th>
  );
}

/** A cell of a dense register row. */
export const REGISTER_CELL =
  "px-5 py-3 align-top text-sm text-text-tertiary [overflow-wrap:anywhere]";

/**
 * A register table in a named region. The table wraps its long ids and sentences to the page's width,
 * so there is nothing to scroll to; the region only stops a table that still overflows from widening
 * the page. It takes no focus of its own: a scroller can hold a tab stop only through a lint option
 * this folder cannot set.
 */
export function RegisterTable({
  name,
  head,
  children,
}: {
  name: string;
  head: ReactNode;
  children: ReactNode;
}) {
  return (
    <div role="region" aria-label={name} className="overflow-x-auto rounded-ds-xs">
      <table className="w-full border-collapse">
        <caption className="sr-only">{name}</caption>
        <thead className="border-b border-border-hairline">
          <tr>{head}</tr>
        </thead>
        {children}
      </table>
    </div>
  );
}

/** The card an Evidence register sits in: its title and delivered count, its sentence, then the body. */
export function RegisterCard({
  title,
  count,
  description,
  action,
  children,
}: {
  title: string;
  /** The delivered count beside the title, or `null` when a filter makes it no longer the number shown. */
  count: string | null;
  description: string;
  /** A control at the right of the title, such as "Download all". */
  action?: ReactNode;
  children: ReactNode;
}) {
  const Heading = SUBSECTION_HEADING;
  return (
    <section className="flex flex-col gap-4 rounded-xl border border-border-subtle bg-surface-card pt-5 shadow-xs">
      <div className="flex flex-wrap items-start justify-between gap-3 px-5">
        <div>
          <Heading className="flex items-center gap-2 font-display text-h4 text-text-primary">
            {title}{" "}
            {count === null ? null : (
              <Badge size="sm" color="gray">
                {count}
              </Badge>
            )}
          </Heading>
          <p className="mt-1 text-small text-text-secondary">{description}</p>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
