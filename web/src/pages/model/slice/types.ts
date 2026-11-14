import type { STATUS_SETS } from "@/components/status/sets";

/** The model group's member of the data file: one record per issuer and run. */
export type ModelSlice = { runs: ModelRun[] };

export type ModelRun = {
  issuer: string;
  run: string;
  header: RunHeader;
  links: RunLinks;
  front: FrontPage;
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
