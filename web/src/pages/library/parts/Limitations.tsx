import { ChevronDown, ChevronUp } from "@untitledui/icons";
import { useId } from "react";
import { Button, Disclosure, DisclosurePanel, Link } from "react-aria-components";
import type { Overview } from "../slice";
import { SECTION_HEADING } from "./heading";
import { TEXT_LINK } from "./links";
import { TRACE_HOST, TraceControl } from "./TraceControl";

/**
 * What the run could not establish (P5): the only collapsible block of a library page. Open by
 * default and always open in print; the link goes to the Evidence gaps.
 */
export function Limitations({
  limitations,
  gapsHref,
}: {
  limitations: Overview["limitations"];
  gapsHref: string;
}) {
  const Heading = SECTION_HEADING;
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="rounded-[14px] border border-border-hairline bg-surface-card p-6 shadow-sm"
    >
      <Disclosure defaultExpanded className="flex flex-col gap-4">
        {({ isExpanded }) => (
          <>
            <div className="flex items-center justify-between gap-3">
              <Heading id={headingId} className="flex items-center gap-2 text-body font-semibold">
                Limitations
                <span className="rounded-ds-full border border-border-hairline bg-surface-subtle px-2 py-0.5 text-xs font-medium text-text-secondary tabular-nums">
                  {limitations.count}
                </span>
              </Heading>
              <div className="flex items-center gap-4">
                <Link
                  href={gapsHref}
                  className={`${TEXT_LINK} text-small font-semibold text-action underline`}
                >
                  {limitations.gapsLink.label}
                </Link>
                <Button
                  slot="trigger"
                  aria-label={isExpanded ? "Collapse limitations" : "Expand limitations"}
                  className="flex size-8 cursor-pointer items-center justify-center rounded-lg text-text-tertiary outline-hidden hover:bg-surface-subtle focus-visible:ring-2 focus-visible:ring-brand"
                >
                  {isExpanded ? (
                    <ChevronUp aria-hidden="true" className="size-4" />
                  ) : (
                    <ChevronDown aria-hidden="true" className="size-4" />
                  )}
                </Button>
              </div>
            </div>
            <DisclosurePanel className="print:block print:[content-visibility:visible]">
              <ul className="flex flex-col gap-3 text-small text-text-secondary">
                {limitations.items.map((item) => (
                  <li
                    key={item.text}
                    className={`${TRACE_HOST} flex max-w-[86ch] items-start gap-3`}
                  >
                    <span className="flex-1">{item.text}</span>
                    <TraceControl trace={item.trace} label="Show sources for this limitation" />
                  </li>
                ))}
              </ul>
            </DisclosurePanel>
          </>
        )}
      </Disclosure>
    </section>
  );
}
