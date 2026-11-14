import { Fragment, useEffect, useId, useRef, useState } from "react";
import { ChevronRight, SearchLg } from "@untitledui/icons";
import { Alert } from "@/components/alert/Alert";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { Badge } from "@/components/base/badges/badges";
import { cx } from "@/utils/cx";
import type { Reader, TraceRow, TraceTable } from "./slice";
import { DerivationTree } from "./parts/DerivationTree";
import { InlineCell } from "./parts/InlineCell";
import { NothingForModule } from "./parts/ModuleFilter";
import {
  PlainHead,
  REGISTER_CELL,
  RegisterCard,
  RegisterTable,
  SortHead,
  sortRows,
  useSort,
  type SortKey,
} from "./parts/RegisterTable";
import { SUBSECTION_HEADING } from "./parts/heading";

type Column = "id" | "module" | "value";

/** What each sortable column is ordered by: the delivered id or module name, or the figure's own sort key. */
function keyOf(row: TraceRow, column: Column): SortKey {
  switch (column) {
    case "id":
      return row.id;
    case "module":
      return row.module;
    case "value":
      return row.value === null || row.value.kind !== "value" ? null : row.value.at;
  }
}

/**
 * The Trace tab: one dense row for each traced item. A row with a calculation opens to its
 * derivation; which rows are open lives in the page, by id, so sorting keeps them open. `item` is the
 * address the page was opened at: that row is open, scrolled into view and focused; one no row holds
 * says so above the table. The caller keys the page by `item`, so a new address starts afresh.
 */
export function EvidenceTrace({
  table,
  count,
  module,
  onClear,
  item,
}: {
  table: TraceTable;
  count: string;
  module: Reader | null;
  onClear: () => void;
  item: string | null;
}) {
  const panels = useId();
  const target = item === null ? null : (table.rows.find((row) => row.id === item) ?? null);
  const [open, setOpen] = useState<ReadonlySet<string>>(
    () => new Set(target?.calc === null || target === null ? [] : [target.id]),
  );
  const [sort, onSort] = useSort<Column>();
  const landed = useRef<HTMLElement | null>(null);
  const land = (element: HTMLElement | null) => {
    landed.current = element;
  };
  useEffect(() => {
    landed.current?.scrollIntoView({ block: "center" });
    landed.current?.focus({ preventScroll: true });
  }, []);
  const unknown =
    item !== null && target === null ? (
      <Alert tone="warning" title="No item has this address">
        {table.emptyText === null
          ? "The table lists every traced item of this run."
          : "This run lists no traced item."}
      </Alert>
    ) : null;
  if (table.emptyText !== null) {
    return (
      <div className="flex flex-col gap-4">
        {unknown}
        <EmptyState>
          <EmptyState.Header>
            <EmptyState.FeaturedIcon icon={SearchLg} />
          </EmptyState.Header>
          <EmptyState.Content>
            <EmptyState.Title as={SUBSECTION_HEADING}>
              Nothing is traced in this run
            </EmptyState.Title>
            <EmptyState.Description>{table.emptyText}</EmptyState.Description>
          </EmptyState.Content>
        </EmptyState>
      </div>
    );
  }
  const held =
    module === null ? table.rows : table.rows.filter((row) => row.moduleId === module.id);
  if (module !== null && held.length === 0) {
    return (
      <NothingForModule
        title={`No traced item sits in ${module.name}`}
        clearLabel="Show all items"
        onClear={onClear}
      />
    );
  }
  const rows = sortRows(held, sort, keyOf);
  const toggle = (id: string) => {
    setOpen((now) => {
      const next = new Set(now);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  };
  const { columns } = table;
  return (
    <div className="flex flex-col gap-4">
      {unknown}
      <RegisterCard
        title={table.title}
        count={module === null ? count : null}
        description={table.description}
      >
        <RegisterTable
          name={table.title}
          head={
            <>
              <PlainHead srOnly>Derivation</PlainHead>
              <SortHead column="id" label={columns.id} sort={sort} onSort={onSort} />
              <PlainHead>{columns.item}</PlainHead>
              <SortHead column="value" label={columns.value} sort={sort} onSort={onSort} />
              <SortHead column="module" label={columns.module} sort={sort} onSort={onSort} />
              <PlainHead>{columns.kind}</PlainHead>
              <PlainHead>{columns.sources}</PlainHead>
            </>
          }
        >
          <tbody>
            {rows.map((row) => {
              const isOpen = open.has(row.id);
              const panel = `${panels}-${row.id}`;
              const here = row.id === target?.id;
              return (
                <Fragment key={row.id}>
                  <tr
                    ref={here && row.calc === null ? land : undefined}
                    tabIndex={here && row.calc === null ? -1 : undefined}
                    className={cx(
                      "border-b border-border-hairline outline-focus-ring focus-visible:outline-2 focus-visible:-outline-offset-2",
                      here && "bg-surface-subtle",
                    )}
                  >
                    <td className="w-9 py-3 pl-3">
                      {row.calc === null ? null : (
                        <button
                          type="button"
                          ref={here ? land : undefined}
                          aria-expanded={isOpen}
                          aria-controls={isOpen ? panel : undefined}
                          aria-label={`Show how ${row.item} was derived`}
                          onClick={() => {
                            toggle(row.id);
                          }}
                          className="rounded-ds-xs p-1 text-text-tertiary outline-hidden focus-visible:ring-2 focus-visible:ring-brand"
                        >
                          <ChevronRight
                            aria-hidden="true"
                            className={cx(
                              "size-4 transition-transform duration-150 motion-reduce:transition-none",
                              isOpen && "rotate-90",
                            )}
                          />
                        </button>
                      )}
                    </td>
                    <th
                      scope="row"
                      className={cx(REGISTER_CELL, "font-mono text-left font-normal")}
                    >
                      {row.id}
                    </th>
                    <td className={cx(REGISTER_CELL, "text-text-primary")}>
                      {row.item}
                      {row.note === null ? null : (
                        <p className="mt-1 text-small text-text-secondary">{row.note}</p>
                      )}
                    </td>
                    <td className={REGISTER_CELL}>
                      <InlineCell cell={row.value} />
                    </td>
                    <td className={REGISTER_CELL}>{row.module}</td>
                    <td className={REGISTER_CELL}>
                      <Badge size="sm" color="gray">
                        {row.kind}
                      </Badge>
                    </td>
                    <td className={cx(REGISTER_CELL, "text-right tabular-nums")}>{row.sources}</td>
                  </tr>
                  {row.calc !== null && isOpen ? (
                    <tr id={panel} className="border-b border-border-hairline">
                      <td colSpan={7} className="px-5 py-3">
                        <DerivationTree node={row.calc} label={`How ${row.item} was derived`} />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </RegisterTable>
      </RegisterCard>
    </div>
  );
}
