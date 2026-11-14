// A Signal page's title: the page's one h1 (the shell draws none for a full-bleed page), at the
// size the mock gives its view heading (`.vh h2`: the design system's h2 step).
import type { ReactNode } from "react";

export function PageTitle({ children }: { children: ReactNode }) {
  return <h1 className="text-h2 text-text-primary">{children}</h1>;
}
