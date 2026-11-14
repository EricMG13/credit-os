import { useRef, useState, type ReactNode } from "react";
import { Link } from "react-aria-components";
import { Alert } from "@/components/alert/Alert";
import { Blocked } from "@/components/gap/Blocked";
import { StatusBadge } from "@/components/status/StatusBadge";
import type { BlockedBody, DeliveredBody, LoadedRun, Module as ModuleData } from "./slice";
import { BottomLine } from "./parts/BottomLine";
import { ChangeViewNote } from "./parts/ChangeViewNote";
import { Findings } from "./parts/Findings";
import { Limitations } from "./parts/Limitations";
import { ModuleNav, type NavSection } from "./parts/ModuleNav";
import { Absent } from "./parts/NotHeld";
import { RunFrame } from "./parts/RunFrame";
import { Section } from "./parts/Section";
import { TRACE_HOST, TraceControl } from "./parts/TraceControl";
import { SECTION_HEADING, SUBSECTION_HEADING } from "./parts/heading";
import { TEXT_LINK, evidenceHref } from "./parts/links";

/** The sections a delivered module has, in page order: the navigator's first group. */
function sectionsOf(body: DeliveredBody): NavSection[] {
  const named = (key: NavSection["key"], label: string): NavSection => ({ key, label });
  return [
    named("bottom-line", "Bottom line"),
    named("findings", "Key findings"),
    ...(body.contrary === null ? [] : [named("contrary", "Contrary evidence")]),
    ...(body.changeView === null ? [] : [named("change-view", "What would change the view")]),
    named("limitations", "Limitations"),
  ];
}

/**
 * Contrary evidence in the mock's 16/26 body with a 600 lead (x.css `.s-alert`; the kit's Alert
 * draws 14px and 500), room for the trace control, and the text at most 72 characters wide.
 */
const CONTRARY =
  "[&>[role=alert]]:pr-12 [&_p]:max-w-[72ch] [&_p]:text-body [&_strong]:text-body [&_strong]:font-semibold";

/** What the navigator scrolls to; focus then goes to the heading it holds. */
function Target({ id, children }: { id: string; children: ReactNode }) {
  return (
    <div data-section={id} className="scroll-mt-6">
      {children}
    </div>
  );
}

function Prose({ body, gapsHref }: { body: DeliveredBody; gapsHref: string }) {
  return (
    <>
      <Target id="bottom-line">
        <BottomLine text={body.bottomLine} level={SUBSECTION_HEADING} />
      </Target>
      <Target id="findings">
        <Section title="Key findings" level={SUBSECTION_HEADING}>
          <Findings findings={body.findings} />
        </Section>
      </Target>
      {body.contrary === null ? null : (
        <Target id="contrary">
          <Section title="Contrary evidence" level={SUBSECTION_HEADING}>
            <div className={`${TRACE_HOST} ${CONTRARY}`}>
              <Alert tone="warning" title={body.contrary.title}>
                {body.contrary.text}
              </Alert>
              <span className="absolute top-3 right-3">
                <TraceControl
                  trace={body.contrary.trace}
                  label="Show sources for the contrary evidence"
                />
              </span>
            </div>
          </Section>
        </Target>
      )}
      {body.changeView === null ? null : (
        <Target id="change-view">
          <ChangeViewNote
            view={body.changeView}
            label="Show sources for the trigger"
            level={SUBSECTION_HEADING}
          />
        </Target>
      )}
      <Target id="limitations">
        <Limitations
          level={SUBSECTION_HEADING}
          limitations={body.limitations}
          gapsHref={gapsHref}
        />
      </Target>
    </>
  );
}

/** A module with nothing to read: why, what that means for the rest of the library, and where the gap is. */
function BlockedModule({
  body,
  state,
  gapsHref,
}: {
  body: BlockedBody;
  state: ModuleData["state"];
  gapsHref: string;
}) {
  return (
    <div className="flex flex-col gap-3">
      {state === "Not assessable" ? (
        <Blocked reason={body.reason} />
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge set="Module state" state={state} />
          <p className="text-small text-text-secondary">{body.reason}</p>
        </div>
      )}
      <p className="max-w-[72ch] text-small text-text-secondary">{body.note}</p>
      <Link
        href={gapsHref}
        className={`${TEXT_LINK} w-fit text-small font-semibold text-action underline`}
      >
        {body.gapsLink.label}
      </Link>
    </div>
  );
}

function ModuleView({
  module,
  run,
  issuer,
}: {
  module: ModuleData;
  run: LoadedRun;
  issuer: string;
}) {
  const Heading = SECTION_HEADING;
  const content = useRef<HTMLDivElement>(null);
  const body = module.body;
  const sections = body.kind === "delivered" ? sectionsOf(body) : [];
  const [active, setActive] = useState<string | null>(sections[0]?.key ?? null);
  const gapsHref = evidenceHref(issuer, run.id, "gaps");
  const goTo = (key: string) => {
    const target = content.current?.querySelector<HTMLElement>(`[data-section="${key}"]`);
    const heading = target?.querySelector<HTMLElement>("h2, h3, h4");
    if (target === null || target === undefined || heading === null || heading === undefined) {
      throw new Error(`the module page has no section "${key}" to move to`);
    }
    target.scrollIntoView();
    heading.focus();
    setActive(key);
  };
  return (
    <div className="grid grid-cols-1 items-start gap-10 min-[1001px]:grid-cols-[240px_minmax(0,1fr)]">
      <ModuleNav
        issuer={issuer}
        run={run.id}
        sections={sections}
        active={active}
        onSection={goTo}
        modules={run.modules}
        current={module.id}
      />
      <div ref={content} className="flex min-w-0 flex-col gap-10">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <Heading className="font-display text-h2 text-text-primary">{module.name}</Heading>
          {body.kind === "delivered" ? (
            <StatusBadge set="Module state" state={module.state} />
          ) : null}
        </div>
        {body.kind === "delivered" ? (
          <Prose body={body} gapsHref={gapsHref} />
        ) : (
          <BlockedModule body={body} state={module.state} gapsHref={gapsHref} />
        )}
      </div>
    </div>
  );
}

/**
 * The Module page of a run: the module `module` names, or the run's first module when the address
 * names none (the Modules tab's index form). A module the run lacks, or a run with none, says so.
 */
export function ModulePage({
  issuer,
  run,
  module,
}: {
  issuer: string | undefined;
  run: string | undefined;
  module: string | undefined;
}) {
  return (
    <RunFrame issuer={issuer} run={run} tab="modules">
      {(loaded, issuerId) => {
        const wanted = module ?? loaded.head.firstModule;
        if (wanted === null) {
          return (
            <Absent title="No modules in this run" description="This run has no module to read." />
          );
        }
        const found = loaded.modules.find((item) => item.id === wanted);
        if (found === undefined) {
          return (
            <Absent title="No such module" description="This run has no module at this address." />
          );
        }
        return (
          <ModuleView
            key={`${issuerId}/${loaded.id}/${found.id}`}
            module={found}
            run={loaded}
            issuer={issuerId}
          />
        );
      }}
    </RunFrame>
  );
}
