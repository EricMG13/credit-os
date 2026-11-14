import { SearchLg } from "@untitledui/icons";
import { Link } from "react-aria-components";
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
 * and the delivered counts, which no longer match what is shown, are not drawn.
 */
export function EvidenceGaps({
  table,
  count,
  module,
  onClear,
  issuer,
  run,
}: {
  table: GapTable;
  count: string;
  module: Reader | null;
  onClear: () => void;
  issuer: string;
  run: string;
}) {
  const [sort, onSort] = useSort<Column>();
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
              <tr key={row.id} className="border-b border-border-hairline">
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
  );
}
