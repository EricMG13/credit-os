import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  /** Badges in a row under the title. */
  badges?: ReactNode;
  /** Actions on the right. */
  actions?: ReactNode;
  /** The page's own header is an h1; a header shown inside a page (the kit) is an h2. */
  as?: "h1" | "h2";
}

export function PageHeader({ title, badges, actions, as: Heading = "h1" }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-4 border-b border-secondary pb-4 lg:flex-row">
        <div className="flex flex-1 flex-col gap-0.5">
          <Heading className="font-display text-h1 text-text-primary">{title}</Heading>
          {badges ? <div className="flex flex-wrap items-center gap-2 pt-2">{badges}</div> : null}
        </div>
        {actions ? <div className="flex items-start gap-3">{actions}</div> : null}
      </div>
    </div>
  );
}
