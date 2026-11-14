import { useId, type ReactNode } from "react";
import { Badge } from "@/components/base/badges/badges";
import { ButtonGroup, ButtonGroupItem } from "@/components/base/button-group/button-group";
import { Tooltip, TooltipTrigger } from "@/components/base/tooltip/tooltip";
import { Tab, TabList, TabPanel, Tabs } from "@/components/application/tabs/tabs";
import { Card } from "@/components/card/Card";
import { Missing } from "@/components/gap/Missing";
import { GapBadge } from "@/components/status/StatusBadge";
import { cx } from "@/utils/cx";
import type { Cell, RowKind, Statement, StatementColumn, StatementsPage } from "../slice/types";
import { TraceControl } from "./TraceControl";

export type StatementView = "figures" | "bars";

/** Every period column is this wide, so equal values draw equal bars in every column. */
const PERIOD = "w-[120px]";
const EMPTY = "w-[220px]";

const LABEL: Record<RowKind, string> = {
  plain: "font-medium",
  subtotal: "pl-7 font-normal text-text-secondary",
  total: "font-semibold",
};

/** The cell a forecast column draws for the chosen case, or the one cell of an actual column. */
function cellFor(entry: Cell | Cell[], column: StatementColumn, caseIndex: number): Cell {
  if (column.kind === "forecast") {
    if (!Array.isArray(entry)) throw new Error(`${column.period}: expected one cell per case`);
    const cell = entry[caseIndex];
    if (cell === undefined)
      throw new Error(`${column.period}: no cell for case ${String(caseIndex)}`);
    return cell;
  }
  if (Array.isArray(entry)) throw new Error(`${column.period}: expected a single cell`);
  return entry;
}

function noteFor(column: StatementColumn, caseIndex: number): string | null {
  if (column.kind === "forecast") {
    const note = column.notes[caseIndex];
    if (note === undefined)
      throw new Error(`${column.period}: no note for case ${String(caseIndex)}`);
    return note.text;
  }
  return column.note;
}

/** A reason is drawn as a tooltip on focus or hover and is the cell's accessible description. */
function Described({ reason, children }: { reason: string | null; children: ReactNode }) {
  const id = useId();
  if (reason === null) return <>{children}</>;
  return (
    <>
      <Tooltip title={reason}>
        <TooltipTrigger
          aria-describedby={id}
          className="cursor-help rounded-ds-xs focus-visible:outline-2 focus-visible:outline-solid focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          {children}
        </TooltipTrigger>
      </Tooltip>
      <span id={id} className="sr-only">
        {reason}
      </span>
    </>
  );
}

function CellBody({ cell, view }: { cell: Cell; view: StatementView }) {
  if (cell.kind === "missing") {
    return (
      <Described reason={cell.reason}>
        <Missing />
      </Described>
    );
  }
  if (cell.kind === "withheld") {
    return (
      <Described reason={cell.reason}>
        <span className="inline-flex items-center gap-2">
          <span
            aria-hidden="true"
            className="withheld-stripes inline-block h-3 w-6 rounded-ds-full"
          />
          <Badge size="sm">Withheld</Badge>
        </span>
      </Described>
    );
  }
  return (
    <>
      {cell.text}
      {view === "bars" ? (
        <i
          data-bar
          data-sign={cell.pos < 0 ? "negative" : "positive"}
          style={{ width: `${(Math.abs(cell.pos) * 100).toFixed(2)}%` }}
          className={cx(
            "mt-1 ml-auto block h-1 min-w-0.5 rounded-xs",
            cell.pos < 0 ? "bg-chart-3" : "bg-chart-1",
          )}
        />
      ) : null}
    </>
  );
}

function Table({
  statement,
  columns,
  caseIndex,
  view,
}: {
  statement: Statement;
  columns: readonly StatementColumn[];
  caseIndex: number;
  view: StatementView;
}) {
  const rowCount = statement.rows.length;
  return (
    <div className="relative overflow-x-auto">
      <table className="w-full min-w-[1100px] table-fixed border-collapse text-body tabular-nums">
        <thead>
          <tr>
            <th
              scope="col"
              className="sticky left-0 bg-surface-card px-3 py-2 text-left font-medium"
            >
              {statement.name}
            </th>
            {columns.map((column, index) => {
              const note = noteFor(column, caseIndex);
              return (
                <th
                  key={index}
                  scope="col"
                  data-forecast={column.kind === "forecast" ? "" : undefined}
                  className={cx(
                    column.kind === "empty" ? EMPTY : PERIOD,
                    "border-b-2 border-border-hairline px-2 py-2 text-right font-medium",
                    column.kind === "forecast" && "bg-surface-canvas",
                  )}
                >
                  {column.period}
                  {note === null ? null : (
                    <span className="block text-caption font-normal text-text-tertiary">
                      {note}
                    </span>
                  )}
                </th>
              );
            })}
            <th scope="col" className="w-9 border-b-2 border-border-hairline">
              <span className="sr-only">Show sources</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {statement.rows.map((row, rowIndex) => {
            let at = 0;
            return (
              <tr
                key={rowIndex}
                data-kind={row.kind}
                className={cx("group/trace group/row", row.kind === "total" && "font-semibold")}
              >
                <th
                  scope="row"
                  className={cx(
                    "sticky left-0 border-t bg-surface-card px-3 py-2 text-left whitespace-normal break-words group-hover/row:bg-surface-subtle",
                    row.kind === "total" ? "border-border-control" : "border-border-hairline",
                    LABEL[row.kind],
                  )}
                >
                  {row.label}
                  {row.gap ? (
                    <span className="ml-2.5 inline-block align-middle font-medium">
                      <GapBadge />
                    </span>
                  ) : null}
                </th>
                {columns.map((column, index) => {
                  if (column.kind === "empty") {
                    return rowIndex === 0 ? (
                      <td
                        key={index}
                        rowSpan={rowCount}
                        className="border-t border-border-hairline px-3 py-2 text-left align-top text-small font-normal text-text-secondary whitespace-normal"
                      >
                        {column.reason}
                      </td>
                    ) : null;
                  }
                  const entry = row.cells[at];
                  if (entry === undefined)
                    throw new Error(`${row.label}: no cell for ${column.period}`);
                  at += 1;
                  const forecast = column.kind === "forecast";
                  return (
                    <td
                      key={index}
                      data-forecast={forecast ? "" : undefined}
                      className={cx(
                        "border-t px-2 py-2 text-right align-middle whitespace-nowrap group-hover/row:bg-surface-subtle",
                        row.kind === "total" ? "border-border-control" : "border-border-hairline",
                        forecast && "bg-surface-canvas",
                      )}
                    >
                      <CellBody cell={cellFor(entry, column, caseIndex)} view={view} />
                    </td>
                  );
                })}
                <td className="w-9 border-t border-border-hairline py-1 pl-2">
                  {row.trace === null ? null : (
                    <TraceControl href={row.trace} label={`Show the sources for ${row.label}`} />
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/**
 * The statements card (R1): heading, the Figures or Bars choice, one tab per statement and the
 * table of the open one, its forecast columns following the chosen case. It computes nothing:
 * a bar's length is the delivered position times the column's width.
 * Kit need: a table with a sticky first column, shaded columns, row kinds and a trace column
 * (the kit table is a sortable collection); a segmented control with a 40px height.
 */
export function StatementTable({
  page,
  caseIndex,
  view,
  onView,
}: {
  page: StatementsPage;
  caseIndex: number;
  view: StatementView;
  onView: (view: StatementView) => void;
}) {
  const first = page.statements[0];
  if (first === undefined) throw new Error("the statements page holds no statement");
  return (
    <Card>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="font-display text-h3 text-text-primary">Statements</h2>
            <p className="text-small text-text-tertiary">{page.intro}</p>
          </div>
          <ButtonGroup
            aria-label="Statements: Figures or Bars"
            disallowEmptySelection
            selectedKeys={[view]}
            onSelectionChange={(keys) => {
              onView(keys.has("bars") ? "bars" : "figures");
            }}
          >
            <ButtonGroupItem id="figures">Figures</ButtonGroupItem>
            <ButtonGroupItem id="bars">Bars</ButtonGroupItem>
          </ButtonGroup>
        </div>
        <Tabs keyboardActivation="automatic" defaultSelectedKey={first.name}>
          <TabList aria-label="Statement">
            {page.statements.map((s) => (
              <Tab key={s.name} id={s.name}>
                {s.name}
              </Tab>
            ))}
          </TabList>
          {page.statements.map((s) => (
            <TabPanel key={s.name} id={s.name} className="pt-4">
              <Table statement={s} columns={page.columns} caseIndex={caseIndex} view={view} />
            </TabPanel>
          ))}
        </Tabs>
        <p className="text-small text-text-tertiary">
          n.a. means the figure is missing, not zero. A zero is written as 0. Shaded columns are
          forecast.
        </p>
      </div>
    </Card>
  );
}
