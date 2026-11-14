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

/** The controls that narrow a list: the search, three selects and three range bands. */
const FILTER_CONTROLS = 7;
/** One applied-filter label for each count from none to every control. */
export const APPLIED_LABELS = FILTER_CONTROLS + 1;

export type LibraryHome = {
  subtitle: string;
  filters: {
    sector: readonly string[];
    pathway: readonly string[];
    state: readonly string[];
    /** One label per number of filters applied, from none to the search, all three selects and all three bands. */
    appliedLabels: readonly string[];
  };
  cards: readonly HomeCard[];
  list: { measures: Record<MeasureKey, MeasureSpec> };
};

/** One run in an issuer's history. `report` and `changes` are absent for a run with nothing to read. */
export type HistoryEntry = {
  asOf: string;
  ran: string;
  state: RunState;
  pathway: string;
  text: string;
  /** The run id its Overview opens on, or `null`. */
  report: string | null;
  /** The delivered "What changed since …" label and the run whose Changes page it opens. */
  changes: { label: string; run: string } | null;
};

/**
 * Newest first, as delivered. `latest` is the run "Open latest report" opens; when it is `null`
 * nothing can be read and `empty` carries the sentence the page shows in place of the feed.
 */
export type History = {
  subtitle: string;
  latest: string | null;
  empty: string | null;
  entries: readonly HistoryEntry[];
};

/** One row of a derivation: `value` is the figure as delivered, `null` when it is not recorded. */
export type TreeNode = {
  label: string;
  value: string | null;
  note: string | null;
  children: readonly TreeNode[];
};

/** What the trace drawer shows for one figure; `evidenceItem` is the item its Evidence page opens. */
export type Trace = {
  /** The dialog's accessible name, for example "Sources for net leverage". */
  title: string;
  /** The drawer's visible heading, for example "Net leverage 4.6x". */
  heading: string;
  /** The line under the title, for example "Capital structure · figure · as of 30 Sep 2026". */
  subtitle: string;
  statement: string;
  derivation: TreeNode;
  /** The quoted passage and where it was read; `null` when the trace has none. */
  excerpt: { quote: string; source: string } | null;
  /** The qualification sentence; `null` when the figure carries none. */
  qualification: string | null;
  evidenceItem: string;
};

/** What the frame of a run page draws above its body. */
export type RunHead = {
  issuerName: string;
  asOf: string;
  pathway: string;
  state: RunState;
  tabs: { modulesCount: string };
  /** The module the Modules tab opens on, or `null` when the run has none. */
  firstModule: string | null;
  /** Where the Forecast tab goes, or `null` while the forecast is not built. */
  forecastHref: string | null;
};

/** The bottom line of a run or module: `trace` is a key of the run's traces, or `null`. */
export type BottomLineText = { label: string; lead: string; rest: string; trace: string | null };

/** One headline figure: `value` is `null` when the figure is missing. */
export type Metric = { label: string; value: Cell; note: string; trace: string | null };

/** One point of For and against; `qualifier` is the label drawn as a badge. */
export type Point = { figure: Cell; text: string; qualifier: string; trace: string | null };

/** One key finding: `number` is delivered text such as "01". */
export type Finding = { number: string; lead: string; body: string; trace: string | null };

/** What would change the view: the title and the passage under it. */
export type ChangeView = { title: string; text: string; trace: string | null };

/** The words of the Dated records set. */
export type DateState = keyof (typeof STATUS_SETS)["Dated records"];

/** One issuer date to watch: `date` is delivered text, never parsed. */
export type DatedItem = { date: string; state: DateState; title: string; text: string };

/** The words of the Module state set. */
export type ModuleState = keyof (typeof STATUS_SETS)["Module state"];

/**
 * One module item. `module` is the module's id, or `null` for an item that stands for several
 * (a repeated state collapsed into one), which opens nothing.
 */
export type ModuleItem = { title: string; lead: string; state: ModuleState; module: string | null };

/** What the run could not establish; `count` and the link's label are delivered text. */
export type Limitations = {
  count: string;
  gapsLink: { label: string };
  items: readonly { text: string; trace: string | null }[];
};

/** The Overview page of a run: bottom line, figures, for and against, findings and dates. */
export type Overview = {
  bottomLine: BottomLineText;
  /** The accessible name of the headline figures. */
  metricsLabel: string;
  metrics: readonly Metric[];
  sides: {
    heading: string;
    note: string;
    columns: readonly { name: string; items: readonly Point[] }[];
  };
  findings: readonly Finding[];
  changeView: ChangeView;
  dates: readonly DatedItem[];
  /** `summary` is delivered text such as "12 of 13 delivered". */
  modules: { summary: string; items: readonly ModuleItem[] };
  limitations: Limitations;
};

/** The words of the Change state set. */
export type ChangeState = keyof (typeof STATUS_SETS)["Change state"];

/** One module's change state; `module` is its id, or `null` for an item that stands for several. */
export type ChangeModuleItem = {
  title: string;
  lead: string;
  state: ChangeState;
  module: string | null;
};

/**
 * One change between two runs. `direction` is delivered, never worked out from the figures; a
 * figure that is not a value (missing, withheld or a gap) has direction "none" and no `change` text.
 * "flat" is a change that is neither up nor down; "none" draws no mark. `kind` and `change` are
 * delivered words such as "Value" and "Lower by 0.3x".
 */
export type Change = {
  measure: string;
  kind: string;
  current: Cell;
  from: Cell;
  direction: "up" | "down" | "flat" | "none";
  change: string | null;
  cause: string;
  effect: string;
  trace: string | null;
};

/** The Changes page of a run: the first run on an issuer has nothing to compare with. */
export type Changes =
  | { kind: "none"; title: string; text: string }
  | {
      kind: "compared";
      heading: string;
      subtitle: string;
      earlierLabel: string;
      currentLabel: string;
      /** The basis note under the table, for example "All six changes, in the order the module wrote them". */
      tableNote: string;
      changes: readonly Change[];
      modules: { summary: string; items: readonly ChangeModuleItem[] };
    };

/**
 * A risk matrix: `columns` heads the Table side (the risk, then the two grades); a grade that is
 * not recorded is `null` and draws "n.a.". `trace` is the block's own, each row has its own.
 */
type MatrixRecord = {
  kind: "matrix";
  title: string;
  note: string | null;
  columns: readonly string[];
  rows: readonly {
    risk: string;
    probability: string | null;
    impact: string | null;
    trace: string | null;
  }[];
  trace: string | null;
};

/** Indicators to watch: `timing` says whether the indicator moves before the credit does or after. */
type WatchRecord = {
  kind: "watch";
  title: string;
  items: readonly {
    indicator: string;
    threshold: string;
    timing: "leading" | "lagging";
    trace: string | null;
  }[];
};

/** The words of the Answer state set. */
export type AnswerState = keyof (typeof STATUS_SETS)["Answer state"];

/**
 * Questions the module set out to answer. `answer` is `null` for a question with none, which
 * carries no trace and is never "Answered".
 */
type QuestionsRecord = {
  kind: "questions";
  title: string;
  items: readonly {
    question: string;
    state: AnswerState;
    answer: string | null;
    trace: string | null;
  }[];
};

/** One block of a module's records. Tasks 10 and 11 add the chart and table kinds. */
export type RecordBlock = MatrixRecord | WatchRecord | QuestionsRecord;

/** What a delivered module says: `contrary` and `changeView` are absent when the module has none. */
export type DeliveredBody = {
  kind: "delivered";
  bottomLine: BottomLineText;
  findings: readonly Finding[];
  contrary: ChangeView | null;
  changeView: ChangeView | null;
  records: readonly RecordBlock[];
  limitations: Limitations;
};

/** A module that could not be delivered: why, the sentence under it and the link's label. */
export type BlockedBody = {
  kind: "blocked";
  reason: string;
  note: string;
  gapsLink: { label: string };
};

/**
 * One module of a run. A delivered body carries "Delivered" or "Delivered with gaps"; a blocked
 * one carries "Not assessable" or "Not run".
 */
export type Module = {
  id: string;
  name: string;
  state: ModuleState;
  body: DeliveredBody | BlockedBody;
};

type RunBase = { id: string; head: RunHead; traces: Record<string, Trace> };

/** A run still loading carries no overview, changes or modules; every other run carries all three. */
export type LoadedRun = RunBase & {
  loading: false;
  overview: Overview;
  changes: Changes;
  modules: readonly Module[];
};
type LoadingRun = RunBase & { loading: true; overview: null; changes: null; modules: null };

/** A run's pages; each task adds its own member. `traces` is keyed by the key a figure carries. */
export type Run = LoadedRun | LoadingRun;

export type Issuer = { id: string; name: string; history: History; runs: readonly Run[] };

export type LibrarySlice = { home: LibraryHome; issuers: readonly Issuer[] };
