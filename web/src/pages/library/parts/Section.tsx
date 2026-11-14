import { useId, type ReactNode } from "react";
import { SECTION_HEADING, SUBSECTION_HEADING } from "./heading";

/** A heading the navigator moves focus to: not in the tab order, with the design focus ring. */
export const FOCUS = "rounded-ds-xs outline-hidden focus-visible:ring-2 focus-visible:ring-brand";

/** The size each heading level takes, so a section under a module name reads as a section. */
const SIZE = { h2: "text-h2", h3: "text-h3", h4: "text-h4" } as const;

/**
 * A page section: a named region under a heading (the mock's `sec-head`), with an optional note set
 * at the right of the heading. `level` is the heading's level, one under the page's by default.
 * `children` is the body.
 */
export function Section({
  title,
  note,
  actions,
  level = SECTION_HEADING,
  children,
}: {
  title: string;
  note?: string;
  /** Controls set at the right of the heading, after the note. */
  actions?: ReactNode;
  level?: typeof SECTION_HEADING | typeof SUBSECTION_HEADING;
  children: ReactNode;
}) {
  const Heading = level;
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-6">
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <Heading
          id={headingId}
          tabIndex={-1}
          className={`font-display ${SIZE[level]} text-text-primary ${FOCUS}`}
        >
          {title}
        </Heading>
        {note === undefined ? null : <span className="text-small text-text-tertiary">{note}</span>}
        {actions}
      </div>
      {children}
    </section>
  );
}

/**
 * A block the mock draws without a visible heading (headline figures, measures): a region named by
 * its title, which a screen reader finds as a heading the navigator can focus. Nothing shows but
 * the design focus ring, drawn on the section while that heading has focus, since the heading is 1px.
 */
export function QuietSection({ title, children }: { title: string; children: ReactNode }) {
  const Heading = SUBSECTION_HEADING;
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="rounded-ds-xs has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand"
    >
      <Heading id={headingId} tabIndex={-1} className="sr-only outline-hidden">
        {title}
      </Heading>
      {children}
    </section>
  );
}
