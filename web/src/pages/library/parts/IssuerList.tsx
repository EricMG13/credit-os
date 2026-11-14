import { useId, useState, type ReactNode } from "react";
import { Link, type SortDescriptor } from "react-aria-components";
import { Table } from "@/components/application/table/table";
import { Tooltip, TooltipTrigger } from "@/components/base/tooltip/tooltip";
import { StatusBadge } from "@/components/status/StatusBadge";
import {
  MEASURES,
  type IssuerCard,
  type LibraryHome,
  type Measure,
  type MeasureKey,
} from "../slice";
import { cardHref } from "./links";

/** The band chosen for each measure: an index into its delivered bands, or `null` for All. */
export type Bands = Record<MeasureKey, number | null>;
export const NO_BANDS: Bands = { leverage: null, netLeverage: null, interestCoverage: null };

type Specs = LibraryHome["list"]["measures"];

/** Only a reported figure takes part in a range or a sort; an adjusted or missing one does not. */
const CELL = "px-3";
const NOWRAP = `${CELL} whitespace-nowrap`;

const screened = (m: Measure): m is NonNullable<Measure> => m !== null && m.basis === "reported";

/** Whether the figure sits in the chosen band (`min` included, `max` excluded); All passes any row. */
function inBand(card: IssuerCard, key: MeasureKey, specs: Specs, band: number | null): boolean {
  if (band === null) return true;
  const m = card.measures[key];
  const range = specs[key].bands[band];
  if (range === undefined) throw new RangeError(`no band ${String(band)} for ${key}`);
  return (
    screened(m) &&
    (range.min === null || m.at >= range.min) &&
    (range.max === null || m.at < range.max)
  );
}

/** Rows ordered by the figure; adjusted and missing figures come last whichever the direction. */
function sorted(rows: readonly IssuerCard[], sort: SortDescriptor | undefined) {
  const key = MEASURES.find((k) => k === sort?.column);
  if (sort === undefined || key === undefined) return rows;
  const sign = sort.direction === "descending" ? -1 : 1;
  const ranked = rows.flatMap((r) => {
    const m = r.measures[key];
    return screened(m) ? [{ r, at: m.at }] : [];
  });
  const rest = rows.filter((r) => !screened(r.measures[key]));
  ranked.sort((a, b) => sign * (a.at - b.at));
  return [...ranked.map((x) => x.r), ...rest];
}

function Figure({ measure }: { measure: NonNullable<Measure> }) {
  const describedBy = useId();
  return (
    <Tooltip title={measure.description}>
      <TooltipTrigger
        aria-describedby={describedBy}
        className="rounded-ds-xs focus-visible:ring-2 focus-visible:ring-brand"
      >
        {measure.text}
        {measure.basis === "adjusted" ? (
          <>
            {" "}
            <span className="text-xs text-text-tertiary">adj.</span>
          </>
        ) : null}
      </TooltipTrigger>
      <span id={describedBy} className="sr-only">
        {measure.description}
      </span>
    </Tooltip>
  );
}

/** The rows a chosen band left out for want of a screenable figure, under the predecessor's heading. */
function Hidden({
  name,
  adjusted,
  rows,
}: {
  name: string;
  adjusted: boolean;
  rows: readonly IssuerCard[];
}) {
  if (rows.length === 0) return null;
  const reason = adjusted
    ? "no figure recorded, or a figure on adjusted EBITDA"
    : "no figure recorded";
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-body font-semibold text-text-primary">{`Hidden by ${name}: ${reason}`}</h2>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-small text-text-secondary">
        {rows.map((r) => (
          <li key={r.issuer}>
            <Link href={cardHref(r.issuer, r.href)} className="underline">
              {r.name}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * One row per issuer: the delivered cells, then the three measures. `rows` already passed the
 * search and selects; `bands` narrow them here, and the rows a band hides for want of a screenable
 * figure are listed beneath. `empty` is drawn when nothing is left.
 */
export function IssuerList({
  home,
  rows,
  bands,
  empty,
}: {
  home: LibraryHome;
  rows: readonly IssuerCard[];
  bands: Bands;
  empty: ReactNode;
}) {
  const [sort, setSort] = useState<SortDescriptor | undefined>(undefined);
  const specs = home.list.measures;
  const shown = sorted(
    rows.filter((r) => MEASURES.every((k) => inBand(r, k, specs, bands[k]))),
    sort,
  );
  const hiddenBy = (k: MeasureKey) =>
    bands[k] === null ? [] : rows.filter((r) => !screened(r.measures[k]));
  return (
    <div className="flex flex-col gap-6">
      {shown.length === 0 ? (
        empty
      ) : (
        <Table
          aria-label="Issuers"
          size="sm"
          className="overflow-x-visible"
          sortDescriptor={sort}
          onSortChange={setSort}
        >
          <Table.Header>
            <Table.Head id="issuer" isRowHeader className={CELL} label="Issuer" />
            <Table.Head id="sector" className={CELL} label="Sector" />
            <Table.Head id="state" className={CELL} label="State" />
            <Table.Head id="asOf" className={CELL} label="As of" />
            <Table.Head id="pathway" className={CELL} label="Pathway" />
            <Table.Head id="modules" className={CELL} label="Modules" />
            {MEASURES.map((k) => (
              <Table.Head
                key={k}
                id={k}
                allowsSorting
                numeric
                className={CELL}
                label={specs[k].name}
              />
            ))}
          </Table.Header>
          <Table.Body>
            {shown.map((r) => (
              <Table.Row key={r.issuer} id={r.issuer}>
                <Table.Cell className={NOWRAP}>
                  <Link href={cardHref(r.issuer, r.href)} className="text-text-primary underline">
                    {r.name}
                  </Link>
                </Table.Cell>
                <Table.Cell className={CELL}>{r.sector}</Table.Cell>
                <Table.Cell className={NOWRAP}>
                  <StatusBadge set="Run states" state={r.state} />
                </Table.Cell>
                <Table.Cell className={NOWRAP}>{r.asOf}</Table.Cell>
                <Table.Cell className={CELL}>{r.pathway}</Table.Cell>
                <Table.Cell className={CELL}>{r.progress.text}</Table.Cell>
                {MEASURES.map((k) => {
                  const m = r.measures[k];
                  return (
                    <Table.Cell key={k} numeric className={NOWRAP}>
                      {m === null ? null : <Figure measure={m} />}
                    </Table.Cell>
                  );
                })}
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      )}
      {MEASURES.map((k) => {
        const hidden = hiddenBy(k);
        return (
          <Hidden
            key={k}
            name={specs[k].name}
            adjusted={hidden.some((r) => r.measures[k]?.basis === "adjusted")}
            rows={hidden}
          />
        );
      })}
      <div className="flex flex-col gap-1 text-small text-text-tertiary">
        {MEASURES.map((k) => (
          <p key={k}>{specs[k].countLine}</p>
        ))}
      </div>
    </div>
  );
}
