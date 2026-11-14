import type { ReactNode } from "react";

/** The route titles: the one source for a route's `title` and for a state's own page h1. */
export const PAGE_NAME = {
  home: "Library",
  history: "Report history",
  overview: "Overview",
  changes: "Changes",
  modules: "Modules",
  forecast: "Forecast",
  evidence: "Evidence",
} as const;

/** The page's h1 where the page draws its own (every library route is full bleed). */
export function PageTitle({ children }: { children: ReactNode }) {
  return <h1 className="font-display text-h1 text-text-primary">{children}</h1>;
}
