import type { Shape } from "./shapes";

export type Tone = "success" | "warning" | "error" | "info" | "neutral" | "action" | "gap";

export interface State {
  shape: Shape;
  tone: Tone;
  word: string;
}

// One entry per state, keyed by its word: the shape and colour family of the design system's
// set table.
function set<W extends string>(states: Record<W, [Shape, Tone]>): Record<W, State> {
  const entries = Object.entries<[Shape, Tone]>(states).map(([word, [shape, tone]]) => [
    word,
    { shape, tone, word },
  ]);
  return Object.fromEntries(entries) as Record<W, State>;
}

export const STATUS_SETS = {
  Status: set({
    Success: ["filled circle", "success"],
    Warning: ["triangle", "warning"],
    Error: ["diamond", "error"],
    Info: ["ring", "info"],
  }),
  "Run states": set({
    Queued: ["ring", "neutral"],
    Running: ["half-filled circle", "action"],
    Finished: ["filled circle", "success"],
    Failed: ["diamond", "error"],
    Capped: ["triangle", "warning"],
    Rejected: ["cross", "neutral"],
    Interrupted: ["pause bars", "warning"],
  }),
  "Signal source states": set({
    Proposed: ["half-filled circle", "info"],
    Approved: ["square", "neutral"],
    Healthy: ["filled circle", "success"],
    Quiet: ["ring", "neutral"],
    Paused: ["pause bars", "neutral"],
    Failing: ["diamond", "error"],
  }),
  "Dated records": set({
    Past: ["filled circle", "neutral"],
    Next: ["half-filled circle", "action"],
    Later: ["ring", "neutral"],
  }),
  "Answer state": set({
    Answered: ["filled circle", "success"],
    "Partly answered": ["half-filled circle", "info"],
    "Not answered": ["ring", "neutral"],
  }),
  "Met or not met": set({
    Met: ["filled circle", "success"],
    "Not met": ["triangle", "warning"],
  }),
  Freshness: set({
    Checked: ["filled circle", "success"],
    "Not checked yet": ["ring", "neutral"],
  }),
  "Module state": set({
    Delivered: ["filled circle", "success"],
    "Delivered with gaps": ["dashed ring", "gap"],
    "Not assessable": ["slashed circle", "neutral"],
    "Not run": ["ring", "neutral"],
  }),
  "Change state": set({
    Changed: ["triangle", "action"],
    Unchanged: ["square", "neutral"],
    "Not assessable": ["slashed circle", "neutral"],
  }),
  "Gap severity": set({
    High: ["diamond", "error"],
    Medium: ["triangle", "warning"],
    Low: ["ring", "neutral"],
  }),
  "File state": set({
    Uploading: ["half-filled circle", "action"],
    "Read in full": ["filled circle", "success"],
    "Read in part": ["triangle", "warning"],
    Unreadable: ["diamond", "error"],
  }),
  Approval: set({
    "Awaiting your approval": ["half-filled circle", "info"],
  }),
  "Activity that cannot be read": set({
    "State not known": ["dashed ring", "gap"],
  }),
};

export type SetName = keyof typeof STATUS_SETS;
