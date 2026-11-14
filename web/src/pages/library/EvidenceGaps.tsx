import { useEffect, useRef } from "react";
import { SearchLg } from "@untitledui/icons";
import { Link } from "react-aria-components";
import { Alert } from "@/components/alert/Alert";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { Badge } from "@/components/base/badges/badges";
import { Missing } from "@/components/gap/Missing";
import { Withheld } from "@/components/gap/Withheld";
import { GapBadge, StatusBadge } from "@/components/status/StatusBadge";
import type { GapForm, GapRow, GapTable, Reader } from "./slice";
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
import { cx } from "@/utils/cx";
import { SUBSECTION_HEADING } from "./parts/heading";
import { TEXT_LINK, modulesHref, overviewHref } from "./parts/links";

type Column = "id" | "module";

const keyOf = (row: GapRow, column: Column): SortKey => (column === "id" ? row.id : row.module);

/** How a gap appears on the findings pages, in the kit's own form for it. */
function ShownAs({ form }: { form: GapForm }) {
  switch (form) {
    case "gap":
      return <GapBadge />;
    case "withheld":
      return <Withheld />;
    case "blocked":
      return <StatusBadge set="Module state" state="Not assessable" />;
    case "missing":
      return <Missing />;
  }
}

/**
 * The Gaps tab: what the run could not establish, in a group for each severity as delivered. Sorting
 * orders the rows inside each group. With a module chosen, a group with none of its gaps drops out,
 * and the delivered counts, which no longer match what is shown, are not drawn. `item` is the gap the
 * address names: that row is marked, scrolled into view and focused; one no gap has says so above the
 * table. The caller keys the page by `item`, so a new address starts afresh.
 */
export function EvidenceGaps({
  table,
  count,
  module,
  onClear,
  issuer,
  run,
  item,
}: {
  table: GapTable;
  count: string;
  module: Reader | null;
  onClear: () => void;
  issuer: string;
  run: string;
  item: string | null;
}) {
  const [sort, onSort] = useSort<Column>();
  const landed = useRef<HTMLTableRowElement>(null);
  useEffect(() => {
    landed.current?.scrollIntoView({ block: "center" });
    landed.current?.focus({ preventScroll: true });
  }, []);
  const unknown =
    item !== null && !table.groups.some((g) => g.rows.some((row) => row.id === item)) ? (
      <Alert tone="warning" title="No gap has this address">
        {table.groups.length === 0
          ? "This run lists no gap."
          : "The table lists every gap of this run."}
      </Alert>
    ) : null;
  const groups = table.groups
    .map((group) => ({
      ...group,
      rows: sortRows(
        module === null ? group.rows : group.rows.filter((row) => row.moduleId === module.id),
        sort,
        keyOf,
      ),
    }))
    .filter((group) => group.rows.length > 0);
  if (table.groups.length === 0) {
    return (
      <EmptyState>
        <EmptyState.Header>
          <EmptyState.FeaturedIcon icon={SearchLg} />
        </EmptyState.Header>
        <EmptyState.Content>
          <EmptyState.Title as={SUBSECTION_HEADING}>This run has no gaps</EmptyState.Title>
          <EmptyState.Description>
            Nothing the modules looked for was missing.
          </EmptyState.Description>
        </EmptyState.Content>
      </EmptyState>
    );
  }
  if (module !== null && groups.length === 0) {
    return (
      <NothingForModule
        title={`No gap sits in ${module.name}`}
        clearLabel="Show all gaps"
        onClear={onClear}
      />
    );
  }
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
              <SortHead column="id" label={columns.id} sort={sort} onSort={onSort} />
              <PlainHead>{columns.gap}</PlainHead>
              <SortHead column="module" label={columns.module} sort={sort} onSort={onSort} />
              <PlainHead>{columns.reason}</PlainHead>
              <PlainHead>{columns.shownAs}</PlainHead>
            </>
          }
        >
          {groups.map((group) => (
            <tbody key={group.severity}>
              <tr className="border-b border-border-hairline bg-surface-subtle">
                <th scope="rowgroup" colSpan={5} className="px-5 py-2 text-left font-semibold">
                  <span className="flex items-center gap-2">
                    <StatusBadge set="Gap severity" state={group.severity} />
                    {module === null ? (
                      <Badge size="sm" color="gray">
                        {group.count}
                      </Badge>
                    ) : null}
                  </span>
                </th>
              </tr>
              {group.rows.map((row) => (
                <tr
                  key={row.id}
                  ref={row.id === item ? landed : undefined}
                  tabIndex={row.id === item ? -1 : undefined}
                  aria-current={row.id === item ? "location" : undefined}
                  className={cx(
                    "border-b border-border-hairline outline-focus-ring focus-visible:outline-2 focus-visible:-outline-offset-2",
                    row.id === item && "bg-surface-subtle",
                  )}
                >
                  <th
                    scope="row"
                    className={`${REGISTER_CELL} font-mono text-left font-normal whitespace-nowrap`}
                  >
                    {row.id}
                  </th>
                  <td className={`${REGISTER_CELL} text-text-primary`}>{row.gap}</td>
                  <td className={REGISTER_CELL}>{row.module}</td>
                  <td className={REGISTER_CELL}>{row.reason}</td>
                  <td className={REGISTER_CELL}>
                    <div className="flex flex-col items-start gap-1.5">
                      <ShownAs form={row.shownAs} />
                      <Link
                        href={
                          row.where.page === "overview"
                            ? overviewHref(issuer, run)
                            : modulesHref(issuer, run, row.moduleId)
                        }
                        className={`${TEXT_LINK} text-small text-text-secondary underline`}
                      >
                        {row.where.label}
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          ))}
        </RegisterTable>
      </RegisterCard>
    </div>
  );
}
