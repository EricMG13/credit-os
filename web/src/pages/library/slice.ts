import type { STATUS_SETS } from "@/components/status/sets";

/** A figure the page draws as written. `null` is missing and draws "n.a."; `at` is for position or sort only. */
export type Cell =
  | null
  | { kind: "value"; text: string; at: number | null }
  | { kind: "withheld"; reason: string | null }
  | { kind: "gap"; reason: string };

/** The words of the Run states set: the state of an issuer's latest run. */
export type RunState = keyof (typeof STATUS_SETS)["Run states"];

/** The three measures the list draws, in column order. */
export const MEASURES = ["leverage", "netLeverage", "interestCoverage"] as const;
export type MeasureKey = (typeof MEASURES)[number];

/**
 * One measure of a run: `null` is not recorded. `at` only sorts and screens; `text` is drawn as
 * delivered. `description` is the delivered EBITDA label with its period, or "Period not recorded".
 */
export type Measure = null | {
  text: string;
  at: number;
  basis: "reported" | "adjusted";
  description: string;
};

/** A delivered range: `min` is included and `max` excluded; `null` is open on that side. */
type Band = { label: string; min: number | null; max: number | null };

export type MeasureSpec = { name: string; countLine: string; bands: readonly Band[] };

export type IssuerCard = {
  kind: "issuer";
  /** The issuer's slug, a key into `LibrarySlice.issuers`. */
  issuer: string;
  name: string;
  sector: string;
  state: RunState;
  lead: string;
  note: string | null;
  asOf: string;
  pathway: string;
  /** `text` is what is shown; `value` and `max` only position the bar. */
  progress: { text: string; value: number; max: number };
  /** The run the card opens on, or `null` when the issuer has no finished run. */
  href: string | null;
  measures: Record<MeasureKey, Measure>;
};

export type HomeCard = IssuerCard | { kind: "loading" };

/** The controls that narrow the cards: the search and three selects. */
const FILTER_CONTROLS = 4;
/** One applied-filter label for each count from none to every control. */
export const APPLIED_LABELS = FILTER_CONTROLS + 1;

export type LibraryHome = {
  subtitle: string;
  filters: {
    sector: readonly string[];
    pathway: readonly string[];
    state: readonly string[];
    /** One label per number of filters applied, from none to the search and all three selects. */
    appliedLabels: readonly string[];
  };
  cards: readonly HomeCard[];
  list: { measures: Record<MeasureKey, MeasureSpec> };
};

export type Issuer = { id: string; name: string };

export type LibrarySlice = { home: LibraryHome; issuers: readonly Issuer[] };
