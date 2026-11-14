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
  return [
    { key: "bottom-line", label: "Bottom line" },
    { key: "findings", label: "Key findings" },
    ...(body.contrary === null ? [] : [{ key: "contrary", label: "Contrary evidence" }]),
    ...(body.changeView === null
      ? []
      : [{ key: "change-view", label: "What would change the view" }]),
    { key: "limitations", label: "Limitations" },
  ];
}

/** What the navigator moves focus to; it is named by the section it holds. */
function Target({ id, children }: { id: string; children: ReactNode }) {
  return (
    <div
      data-section={id}
      tabIndex={-1}
      className="scroll-mt-6 rounded-ds-xs outline-hidden focus-visible:ring-2 focus-visible:ring-brand"
    >
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
            <div className={`${TRACE_HOST} [&>[role=alert]]:pr-12`}>
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
  const [active, setActive] = useState(sections[0]?.key ?? "");
  const gapsHref = evidenceHref(issuer, run.id, "gaps");
  const goTo = (key: string) => {
    const target = content.current?.querySelector<HTMLElement>(`[data-section="${key}"]`);
    if (target === null || target === undefined) return;
    target.scrollIntoView();
    target.focus();
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
          {body.kind === "delivered" && module.state !== "Delivered" ? (
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
 * The Module page of a run: the module `module` names. A module the run lacks says so.
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
        const found = loaded.modules.find((item) => item.id === module);
        if (found === undefined) {
          return (
            <Absent title="No such module" description="This run has no module at this address." />
          );
        }
        return <ModuleView key={found.id} module={found} run={loaded} issuer={issuerId} />;
      }}
    </RunFrame>
  );
}
