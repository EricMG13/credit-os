import { Callout } from "@/components/alert/Alert";
import type { ChangeView } from "../slice";
import { SECTION_HEADING, type SUBSECTION_HEADING } from "./heading";
import { Section } from "./Section";
import { TRACE_HOST, TraceControl } from "./TraceControl";

/**
 * What would change the view: the kit's info Callout under its heading, with its one trace control
 * at the corner. `label` is the control's accessible name, which the mock words per page.
 */
export function ChangeViewNote({
  view,
  label,
  level = SECTION_HEADING,
}: {
  view: ChangeView;
  label: string;
  level?: typeof SECTION_HEADING | typeof SUBSECTION_HEADING;
}) {
  return (
    <Section title="What would change the view" level={level}>
      <div className={`${TRACE_HOST} [&>[role=note]]:pr-12`}>
        <Callout title={view.title}>{view.text}</Callout>
        <span className="absolute top-3 right-3">
          <TraceControl trace={view.trace} label={label} />
        </span>
      </div>
    </Section>
  );
}
