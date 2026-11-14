import type { ReactNode } from "react";
import { ChevronRight } from "@untitledui/icons";
import { StatusBadge } from "@/components/status/StatusBadge";

const ROW =
  "group/trace flex items-center gap-4 rounded-ds-md border border-border-hairline bg-surface-card p-4";

/**
 * A list row: title and sentence, a trace control, then a chevron when `href` is given or the
 * kit's "Not assessable" badge when it is not (the row then is no link and keeps its place).
 * The trace control sits beside the link, not inside it, so pressing it follows no page link.
 */
export function Item({
  title,
  text,
  href,
  trace,
}: {
  title: string;
  text: string;
  href: string | null;
  trace: ReactNode;
}) {
  const body = (
    <>
      <span
        aria-hidden="true"
        className="flex size-8 flex-none items-center justify-center rounded-ds-sm bg-surface-subtle text-text-tertiary"
      >
        <i className="size-5 rounded-ds-sm border-[1.5px] border-current" />
      </span>
      <span className="min-w-0 flex-1">
        <b className="block text-sm font-medium text-text-primary">{title}</b>
        <span className="block text-sm text-text-secondary">{text}</span>
      </span>
    </>
  );
  if (href === null) {
    return (
      <div data-item className={ROW}>
        {body}
        {trace}
        <StatusBadge set="Module state" state="Not assessable" />
      </div>
    );
  }
  return (
    <div data-item className={ROW}>
      <a
        href={href}
        className="flex min-w-0 flex-1 items-center gap-4 outline-focus focus-visible:outline-2 focus-visible:outline-offset-2"
      >
        {body}
      </a>
      {trace}
      <ChevronRight aria-hidden="true" className="size-4 flex-none text-text-tertiary" />
    </div>
  );
}
