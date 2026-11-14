import type { STATUS_SETS } from "@/components/status/sets";

/** The model group's member of the data file: one record per issuer and run. */
export type ModelSlice = { runs: ModelRun[] };

export type ModelRun = {
  issuer: string;
  run: string;
  header: RunHeader;
  links: RunLinks;
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
