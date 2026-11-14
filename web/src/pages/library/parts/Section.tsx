import { useId, type ReactNode } from "react";
import { SECTION_HEADING } from "./heading";

/**
 * A page section: a named region under an h2 (the mock's `sec-head`), with an optional note set at
 * the right of the heading. `children` is the body.
 */
export function Section({
  title,
  note,
  children,
}: {
  title: string;
  note?: string;
  children: ReactNode;
}) {
  const Heading = SECTION_HEADING;
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-6">
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <Heading id={headingId} className="font-display text-h2 text-text-primary">
          {title}
        </Heading>
        {note === undefined ? null : <span className="text-small text-text-tertiary">{note}</span>}
      </div>
      {children}
    </section>
  );
}
