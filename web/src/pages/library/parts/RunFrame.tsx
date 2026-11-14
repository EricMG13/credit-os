import { useState, type ReactNode } from "react";
import { Link } from "react-aria-components";
import { Badge } from "@/components/base/badges/badges";
import { StatusBadge } from "@/components/status/StatusBadge";
import { PageHeader } from "@/shell/PageHeader";
import { cx } from "@/utils/cx";
import type { Run, RunHead } from "../slice";
import { ButtonLink } from "./ButtonLink";
import { LibraryPage } from "./LibraryPage";
import { NotHeld } from "./NotHeld";
import { SourcesSwitch } from "./SourcesSwitch";
import { ISSUER_HEADING } from "./heading";
import {
  LIBRARY_HOME,
  RUN_START,
  TEXT_LINK,
  changesHref,
  evidenceHref,
  historyHref,
  modulesHref,
  overviewHref,
} from "./links";

export type RunTab = "overview" | "changes" | "modules" | "forecast" | "evidence";

const TAB =
  "inline-flex h-9 items-center gap-1.5 border-b-2 border-transparent px-0.5 pb-2.5 text-md font-semibold whitespace-nowrap";

/** One tab: a link between routes, or plain disabled text when the run has nowhere to send it. */
function RunTabLink({
  href,
  current,
  label,
  count,
  hint,
}: {
  href: string | null;
  current: boolean;
  label: string;
  count?: string;
  hint?: string;
}) {
  const badge =
    count === undefined ? null : (
      <Badge size="sm" color={current ? "brand" : "gray"}>
        {count}
      </Badge>
    );
  if (href === null) {
    return (
      <span aria-disabled="true" className={cx(TAB, "cursor-not-allowed text-text-disabled")}>
        {label}
        {badge}
        {hint === undefined ? null : <span className="text-xs font-normal">{hint}</span>}
      </span>
    );
  }
  return (
    <Link
      href={href}
      aria-current={current ? "page" : undefined}
      className={cx(
        TAB,
        TEXT_LINK,
        "text-text-tertiary hover:border-action hover:text-action",
        current && "border-action text-action",
      )}
    >
      {label}
      {badge}
    </Link>
  );
}

function RunTabs({ issuer, run, tab }: { issuer: string; run: Run; tab: RunTab }) {
  const { head } = run;
  const here = (name: RunTab) => tab === name;
  return (
    <nav aria-label="Run pages" className="flex flex-wrap gap-3 border-b border-border-hairline">
      <RunTabLink href={overviewHref(issuer, run.id)} current={here("overview")} label="Overview" />
      <RunTabLink href={changesHref(issuer, run.id)} current={here("changes")} label="Changes" />
      <RunTabLink
        href={head.firstModule === null ? null : modulesHref(issuer, run.id, head.firstModule)}
        current={here("modules")}
        label="Modules"
        count={head.tabs.modulesCount}
      />
      <RunTabLink
        href={head.forecastHref}
        current={here("forecast")}
        label="Forecast"
        hint="Not built yet"
      />
      <RunTabLink
        href={evidenceHref(issuer, run.id, "summary")}
        current={here("evidence")}
        label="Evidence"
      />
    </nav>
  );
}

function RunHeader({
  issuer,
  head,
  sources,
}: {
  issuer: string;
  head: RunHead;
  sources: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2.5">
      <Link
        href={LIBRARY_HOME}
        className={`${TEXT_LINK} w-fit text-small text-text-tertiary underline`}
      >
        Library
      </Link>
      <PageHeader
        as={ISSUER_HEADING}
        title={head.issuerName}
        badges={
          <>
            <Badge>{head.asOf}</Badge>
            <Badge>{head.pathway}</Badge>
            <StatusBadge set="Run states" state={head.state} />
          </>
        }
        actions={
          <>
            {sources}
            <ButtonLink href={historyHref(issuer)} color="secondary">
              Report history
            </ButtonLink>
            <ButtonLink href={RUN_START}>New run</ButtonLink>
          </>
        }
      />
    </div>
  );
}

const BAR = "rounded-ds-xs bg-surface-subtle";

/** The static skeleton of a run still loading: the shape of what will arrive, nothing moving. */
function RunSkeleton() {
  const metric = (title: string, value: string, note: string) => (
    <div className="flex flex-1 flex-col gap-2 rounded-ds-md border border-border-hairline p-4">
      <div className={cx(BAR, "h-4", title)} />
      <div className={cx(BAR, "h-9.5", value)} />
      <div className={cx(BAR, "h-4", note)} />
    </div>
  );
  const item = (title: string, text: string) => (
    <div className="flex gap-3">
      <div className={cx(BAR, "h-4 w-5")} />
      <div className="flex flex-1 flex-col gap-2">
        <div className={cx(BAR, "h-4", title)} />
        <div className={cx(BAR, "h-4", text)} />
      </div>
    </div>
  );
  return (
    <div aria-busy="true" className="flex flex-col gap-5">
      <div className={cx(BAR, "h-33 rounded-[10px]")} />
      <div className="flex gap-4">
        {metric("w-1/2", "w-[70%]", "w-4/5")}
        {metric("w-1/2", "w-3/5", "w-[70%]")}
        {metric("w-1/2", "w-[70%]", "w-3/5")}
      </div>
      <div className="flex flex-col gap-4">
        {item("w-[30%]", "w-[85%]")}
        {item("w-[36%]", "w-[70%]")}
      </div>
    </div>
  );
}

/**
 * Wraps every run page: the run header, the Show sources switch and the run tabs. `children` is
 * the page body; a run still loading draws the skeleton in its place.
 */
export function RunFrame({
  issuer: issuerId,
  run: runId,
  tab,
  children,
}: {
  issuer: string | undefined;
  run: string | undefined;
  tab: RunTab;
  children: ReactNode;
}) {
  const [sources, setSources] = useState(false);
  return (
    <LibraryPage>
      {({ issuers }) => {
        const issuer = issuers.find((item) => item.id === issuerId);
        if (issuer === undefined) {
          return (
            <NotHeld
              title="No such issuer"
              description="The library holds no issuer at this address."
            />
          );
        }
        const run = issuer.runs.find((item) => item.id === runId);
        if (run === undefined) {
          return (
            <NotHeld title="No such run" description="This issuer has no run at this address." />
          );
        }
        return (
          <div data-sources={sources ? "on" : "off"} className="flex flex-col gap-8">
            <div className="flex flex-col gap-5">
              <RunHeader
                issuer={issuer.id}
                head={run.head}
                sources={<SourcesSwitch isSelected={sources} onChange={setSources} />}
              />
              <RunTabs issuer={issuer.id} run={run} tab={tab} />
            </div>
            {run.loading ? <RunSkeleton /> : children}
          </div>
        );
      }}
    </LibraryPage>
  );
}
