import type { STATUS_SETS } from "@/components/status/sets";

/** The model group's member of the data file: one record per issuer and run. */
export type ModelSlice = { runs: ModelRun[] };

export type ModelRun = {
  issuer: string;
  run: string;
  header: RunHeader;
  links: RunLinks;
  /** The forecast cases, in the order the page offers them; the first is the default. */
  cases: CaseCard[];
  front: FrontPage;
  statements: StatementsPage;
  limitations: LimitationsPage;
};

/** A word of the status kit's "Run states" set. */
export type RunState = keyof (typeof STATUS_SETS)["Run states"];

export type RunHeader = {
  issuerName: string;
  /** The whole badge text, for example "As of 30 June 2025". */
  asOf: string;
  purpose: string;
  state: RunState;
  sample: boolean;
};

/** Addresses written by delivery; the model pages follow them and build none. */
export type RunLinks = { library: string; report: string; evidence: string; evidenceGaps: string };

export type LimitationsPage = {
  count: string;
  gapsLinkText: string;
  lead: string;
  items: Limitation[];
  notEstablished: { count: string; items: GapItem[] };
};

export type Limitation = {
  title: string;
  label: string;
  text: string;
  /** An address into the run's Evidence; `null` draws no trace control. */
  trace: string | null;
};

export type GapItem = { title: string; reason: string };

export type FrontPage = {
  bottomLine: { lead: string; rest: string; trace: string | null };
  headline: { period: string; metrics: Metric[] };
  covers: { facts: Fact[] };
  parts: Part[];
};

/** A headline figure: the display string, or missing (`text: null`), or withheld. */
export type MetricValue = { text: string | null } | { withheld: true };

export type Metric = {
  label: string;
  /** What the figure measures, drawn as a tooltip; never a source. */
  definition: string;
  value: MetricValue;
  /** The whole delta line, arrow included; `null` draws none. */
  delta: string | null;
  /** A sentence under a missing or withheld value. */
  note: string | null;
  trace: string | null;
};

export type Fact = { label: string; value: string; trace: string | null };

/** The pages of this group a part can open. */
export type PartPage = "analysis" | "statements" | "portfolio-fit";

/** A part of the model; `to: null` is a part that could not be assessed and links nowhere. */
export type Part = { title: string; text: string; to: PartPage | null; trace: string | null };

/** A forecast case as its card draws it. The page adds no wording but the "Leaves out: " lead. */
export type CaseCard = {
  name: string;
  tag: string;
  assumption: string;
  leavesOut: string;
  /** A line drawn under the card, for example the stress case's note; `null` draws none. */
  note: string | null;
  trace: string | null;
};

export type StatementsPage = {
  /** The line under the heading: units and fiscal year end. */
  intro: string;
  columns: StatementColumn[];
  statements: Statement[];
  /** The bridges, each drawn for the chosen case. */
  bridges: Bridge[];
  /** The two cases side by side; the cases are the first two of `ModelRun.cases`. */
  comparison: Comparison;
  debt: { stack: Stack; maturities: ColumnsData };
  recovery: ColumnsData;
  /** The gap panel: the title is joined to the reason by the page. */
  gap: GapItem;
  checkFigure: { title: string; text: string; href: string };
  /** The published model, as a file to download; `null` when the run has none. */
  published: Published | null;
};

export type Published = { kind: "markdown" | "html"; href: string };

/**
 * What every chart carries besides its marks: the words around it and its trace address. Every
 * address in this slice that leads into the library (a `trace`, `links`, a tab's or a
 * limitations link's `href`) starts with `#/`; `published.href` and `checkFigure.href` (files)
 * are not covered by that rule.
 *
 * The two sides of one chart state the same thing for one record: wherever a table cell states a
 * mark, the cell is `null` exactly where the mark is missing and holds the mark's text where it is
 * drawn. The mapping per kind is written on the type that carries the cells.
 */
type ChartInfo = { title: string; subtitle: string; note: string; trace: string | null };

/** A caller tick: a position on the axis and the exact label drawn there. */
export type Tick = { value: number; label: string };

/**
 * A bridge step. `from` and `to` are positions on the axis only; `text` is the exact signed
 * label. A missing step carries nothing else.
 */
export type BridgeStep =
  | PresentStep<"total">
  | PresentStep<"up">
  | PresentStep<"down">
  | { label: string; kind: "missing" };

type PresentStep<K extends string> = {
  label: string;
  kind: K;
  from: number;
  to: number;
  text: string;
};

/**
 * One walk. `caseSteps` holds one list of steps per case, in case order; the table holds one row
 * per step with one cell per case, `null` where the step is missing.
 */
export type Bridge = ChartInfo & {
  yTicks: Tick[];
  caseSteps: BridgeStep[][];
  /** The first entry heads the label column; the rest are the case names. */
  head: string[];
  rows: { label: string; cells: (string | null)[]; trace: string | null }[];
};

/** One measure of the side by side chart: a position and the exact text for each case. */
export type ComparisonPanel = {
  measure: string;
  /** The label of this panel's row in the table, which may be shorter than the measure. */
  tableLabel: string;
  /** The panel's own axis maximum; a bar is its value over it. */
  max: number;
  values: [number | null, number | null];
  /** `null` exactly where the value is missing. */
  texts: [string | null, string | null];
  trace: string | null;
};

export type Comparison = ChartInfo & {
  /** The names beside each bar; shorter than the case names. */
  rowLabels: [string, string];
  /** The table's first column heading. */
  tableHead: string;
  panels: ComparisonPanel[];
};

export type StackPart = {
  name: string;
  value: number;
  text: string;
  share: string;
  trace: string | null;
};

/** One bar split into ranked parts; `head` is the label, amount and share headings. */
export type Stack = ChartInfo & { head: string[]; parts: StackPart[] };

/** Bars by group and series, such as maturities by year; the table is the labels as drawn. */
export type ColumnsData = ChartInfo & {
  yTicks: Tick[];
  /** The table's first column heading. */
  head: string;
  groups: { label: string; trace: string | null }[];
  series: { name: string; values: (number | null)[]; labels: (string | null)[] }[];
};
/** One header note per case, in the order of `ModelRun.cases`. */
type CaseNote = { text: string };

/**
 * A period column. An actual column has one note; a forecast column follows the chosen case and
 * has one note per case; an empty column is drawn as its header and its reason, with no cells.
 */
export type StatementColumn =
  | { kind: "actual"; period: string; note: string }
  | { kind: "forecast"; period: string; notes: CaseNote[] }
  | { kind: "empty"; period: string; note: string | null; reason: string };

export type Statement = { name: string; rows: StatementRow[] };

export type RowKind = "plain" | "subtotal" | "total";

export type StatementRow = {
  label: string;
  kind: RowKind;
  /** Draws the kit's "Not established for this run" badge beside the label. */
  gap: boolean;
  trace: string | null;
  /**
   * One entry per column that is not empty, in column order: a cell for an actual column, a list
   * of cells (one per case) for a forecast column.
   */
  cells: (Cell | Cell[])[];
};

/**
 * A figure is the display string plus a position for the Bars view, signed and relative to the
 * row's largest magnitude (-1 to 1). Missing and withheld carry an optional sentence.
 */
export type Cell =
  | { kind: "figure"; text: string; pos: number }
  | { kind: "missing"; reason: string | null }
  | { kind: "withheld"; reason: string | null };
