import { createContext } from "react";
import type { Trace } from "../slice";

/** What a run page's trace controls need from the frame they sit in: the run's traces and the drawer. */
export type RunContextValue = {
  traces: Readonly<Record<string, Trace>>;
  open: (key: string) => void;
};

export const RunContext = createContext<RunContextValue | null>(null);
