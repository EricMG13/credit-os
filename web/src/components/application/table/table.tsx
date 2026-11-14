import type { ComponentPropsWithRef, Ref, TdHTMLAttributes, ThHTMLAttributes } from "react";
import { createContext, useContext } from "react";
import { ArrowDown, ChevronSelectorVertical } from "@untitledui/icons";
import type {
  CellProps as AriaCellProps,
  ColumnProps as AriaColumnProps,
  RowProps as AriaRowProps,
  TableHeaderProps as AriaTableHeaderProps,
  TableProps as AriaTableProps,
} from "react-aria-components";
import {
  Cell as AriaCell,
  Collection as AriaCollection,
  Column as AriaColumn,
  Group as AriaGroup,
  Row as AriaRow,
  Table as AriaTable,
  TableBody as AriaTableBody,
  TableHeader as AriaTableHeader,
} from "react-aria-components";
import { Missing } from "@/components/gap/Missing";
import { cx } from "@/utils/cx";

const TableContext = createContext<{ size: "sm" | "md" }>({ size: "md" });

interface TableRootProps
  extends AriaTableProps, Omit<ComponentPropsWithRef<"table">, "className" | "slot" | "style"> {
  /** Controls the density of the header, rows and cells. */
  size?: "sm" | "md";
}

const TableRoot = ({ className, size = "md", ...props }: TableRootProps) => {
  return (
    <TableContext.Provider value={{ size }}>
      <div className="overflow-x-auto">
        <AriaTable
          className={(state) =>
            cx(
              "w-full overflow-x-hidden",
              typeof className === "function" ? className(state) : className,
            )
          }
          {...props}
        />
      </div>
    </TableContext.Provider>
  );
};
TableRoot.displayName = "Table";

interface TableHeaderProps<T extends object>
  extends
    AriaTableHeaderProps<T>,
    Omit<ComponentPropsWithRef<"thead">, "children" | "className" | "slot" | "style"> {
  /** Controls the height of the header row. Falls back to the size inherited from the table. */
  size?: "sm" | "md";
}

const TableHeader = <T extends object>({
  columns,
  children,
  className,
  size: sizeProp,
  ...props
}: TableHeaderProps<T>) => {
  const context = useContext(TableContext);
  const size = sizeProp ?? context.size;

  return (
    <AriaTableHeader
      {...props}
      className={(state) =>
        cx(
          "relative bg-secondary",
          size === "sm" ? "h-9" : "h-11",

          // Row border—using an "after" pseudo-element to avoid the border taking up space.
          "[&>tr>th]:after:pointer-events-none [&>tr>th]:after:absolute [&>tr>th]:after:inset-x-0 [&>tr>th]:after:bottom-0 [&>tr>th]:after:h-px [&>tr>th]:after:bg-border-secondary [&>tr>th]:focus-visible:after:bg-transparent",

          typeof className === "function" ? className(state) : className,
        )
      }
    >
      <AriaCollection items={columns}>{children}</AriaCollection>
    </AriaTableHeader>
  );
};
TableHeader.displayName = "TableHeader";

interface TableHeadProps
  extends
    AriaColumnProps,
    Omit<ThHTMLAttributes<HTMLTableCellElement>, "children" | "className" | "style" | "id"> {
  /** The column heading text, rendered before any children. */
  label?: string;
  /** Right-aligns the heading over a numeric column. */
  numeric?: boolean;
}

const TableHead = ({ className, label, numeric, children, ...props }: TableHeadProps) => {
  const { size } = useContext(TableContext);

  return (
    <AriaColumn
      {...props}
      className={(state) =>
        cx(
          "relative p-0 py-2 outline-hidden focus-visible:z-1 focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-bg-primary focus-visible:ring-inset",
          size === "sm" ? "px-5" : "px-6",
          state.allowsSorting && "cursor-pointer",
          typeof className === "function" ? className(state) : className,
        )
      }
    >
      {(state) => (
        <AriaGroup className={cx("flex items-center gap-1", numeric && "justify-end")}>
          <div className="flex items-center gap-1">
            {label && (
              <span className="text-xs font-semibold whitespace-nowrap text-quaternary">
                {label}
              </span>
            )}
            {typeof children === "function" ? children(state) : children}
          </div>

          {state.allowsSorting &&
            (state.sortDirection ? (
              <ArrowDown
                className={cx(
                  "size-3 stroke-[3px] text-fg-quaternary",
                  state.sortDirection === "ascending" && "rotate-180",
                )}
              />
            ) : (
              <ChevronSelectorVertical size={12} strokeWidth={3} className="text-fg-quaternary" />
            ))}
        </AriaGroup>
      )}
    </AriaColumn>
  );
};
TableHead.displayName = "TableHead";

interface TableRowProps<T extends object>
  extends
    AriaRowProps<T>,
    Omit<
      ComponentPropsWithRef<"tr">,
      "children" | "className" | "onClick" | "slot" | "style" | "id"
    > {
  /** Controls the height of the row. Falls back to the size inherited from the table. */
  size?: "sm" | "md";
}

const TableRow = <T extends object>({
  columns,
  children,
  className,
  size: sizeProp,
  ...props
}: TableRowProps<T>) => {
  const context = useContext(TableContext);
  const size = sizeProp ?? context.size;

  return (
    <AriaRow
      {...props}
      className={(state) =>
        cx(
          "relative outline-focus-ring transition-colors after:pointer-events-none hover:bg-secondary focus-visible:outline-2 focus-visible:-outline-offset-2",
          size === "sm" ? "h-14" : "h-18",

          // Row border—using an "after" pseudo-element to avoid the border taking up space.
          "[&>td]:after:absolute [&>td]:after:inset-x-0 [&>td]:after:bottom-0 [&>td]:after:h-px [&>td]:after:w-full [&>td]:after:bg-border-secondary last:[&>td]:after:hidden [&>td]:focus-visible:after:opacity-0 focus-visible:[&>td]:after:opacity-0",

          typeof className === "function" ? className(state) : className,
        )
      }
    >
      <AriaCollection items={columns}>{children}</AriaCollection>
    </AriaRow>
  );
};
TableRow.displayName = "TableRow";

interface TableCellProps
  extends
    AriaCellProps,
    Omit<TdHTMLAttributes<HTMLTableCellElement>, "children" | "className" | "style" | "id"> {
  ref?: Ref<HTMLTableCellElement>;
  /** Right-aligns the cell with tabular numerals, for a numeric column. */
  numeric?: boolean;
}

/** A `null` child is a figure that is missing, and is drawn as "n.a." (never as 0). */
const TableCell = ({ className, children, numeric, ...props }: TableCellProps) => {
  const { size } = useContext(TableContext);

  return (
    <AriaCell
      {...props}
      className={(state) =>
        cx(
          "relative text-sm text-tertiary outline-focus-ring focus-visible:z-1 focus-visible:outline-2 focus-visible:-outline-offset-2",
          size === "sm" && "px-5 py-3",
          size === "md" && "px-6 py-4",
          numeric && "text-right tabular-nums",

          typeof className === "function" ? className(state) : className,
        )
      }
    >
      {children === null ? <Missing /> : children}
    </AriaCell>
  );
};
TableCell.displayName = "TableCell";

const Table = TableRoot as typeof TableRoot & {
  Body: typeof AriaTableBody;
  Cell: typeof TableCell;
  Head: typeof TableHead;
  Header: typeof TableHeader;
  Row: typeof TableRow;
};
Table.Body = AriaTableBody;
Table.Cell = TableCell;
Table.Head = TableHead;
Table.Header = TableHeader;
Table.Row = TableRow;

export { Table };
