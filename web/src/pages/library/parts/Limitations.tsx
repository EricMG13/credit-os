import { ChevronDown, ChevronUp } from "@untitledui/icons";
import { Button, Disclosure, DisclosurePanel, Link } from "react-aria-components";
import type { Limitations as LimitationsData } from "../slice";
import type { SECTION_HEADING, SUBSECTION_HEADING } from "./heading";
import { TEXT_LINK } from "./links";
import { TRACE_HOST, TraceControl } from "./TraceControl";

/**
 * What the run or module could not establish (P5): the only collapsible block of a library page.
 * Open by default and always open in print; the link goes to the Evidence gaps. `level` is the
 * heading's level.
 */
export function Limitations({
  limitations,
  gapsHref,
  level,
}: {
  limitations: LimitationsData;
  gapsHref: string;
  level: typeof SECTION_HEADING | typeof SUBSECTION_HEADING;
}) {
  const Heading = level;
  return (
    <section
      aria-label="Limitations"
      className="rounded-[14px] border border-border-hairline bg-surface-card p-6 shadow-sm"
    >
      <Disclosure defaultExpanded className="flex flex-col gap-4">
        {({ isExpanded }) => (
          <>
            <div className="flex items-center justify-between gap-3">
              <Heading className="flex items-center gap-2 text-body font-semibold">
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
