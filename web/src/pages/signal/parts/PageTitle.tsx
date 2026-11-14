// A Signal page's title: the page's one h1 (the shell draws none for a full-bleed page).
import type { ReactNode } from "react";

export function PageTitle({ children }: { children: ReactNode }) {
  return <h1 className="text-xl font-semibold text-text-primary">{children}</h1>;
}
