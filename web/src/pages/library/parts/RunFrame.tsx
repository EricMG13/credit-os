import { useState, type ReactNode } from "react";
import { Link } from "react-aria-components";
import { Badge } from "@/components/base/badges/badges";
import { StatusBadge } from "@/components/status/StatusBadge";
import { PageHeader } from "@/shell/PageHeader";
import { cx } from "@/utils/cx";
import type { LoadedRun, Run, RunHead } from "../slice";
import { Button } from "@/components/base/buttons/button";
import { LibraryPage } from "./LibraryPage";
import { NotHeld } from "./NotHeld";
import { PAGE_NAME } from "./PageTitle";
import { RunContext } from "./RunContext";
import { SourcesSwitch, useSourcesOn } from "./SourcesSwitch";
import { TraceDrawer } from "./TraceDrawer";
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
  traceItemHref,
} from "./links";

export type RunTab = "overview" | "changes" | "modules" | "forecast" | "evidence";

const TAB =
  "inline-flex items-center gap-1.5 border-b-2 border-transparent whitespace-nowrap font-semibold";
const TAB_SIZE = {
  md: "h-9 px-1.5 pb-2.5 text-md",
  sm: "h-8 px-1 pb-2.5 text-sm",
} as const;

/** One tab: a link between routes, or plain disabled text when the run has nowhere to send it. */
export function RunTabLink({
  href,
  current,
  label,
  count,
  hint,
  small = false,
}: {
  href: string | null;
  current: boolean;
  label: string;
  count?: string;
  hint?: string;
  /** The smaller tab of a page's own section tabs (the mock's `u-tab-sm`). */
  small?: boolean;
}) {
  const size = TAB_SIZE[small ? "sm" : "md"];
  const badge =
    count === undefined ? null : (
      <Badge size="sm" color={current ? "brand" : "gray"}>
        {count}
      </Badge>
    );
  if (href === null) {
    return (
      <span aria-disabled="true" className={cx(TAB, size, "cursor-not-allowed text-text-disabled")}>
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
        size,
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
            <Button href={historyHref(issuer)} color="secondary">
              Report history
            </Button>
            <Button href={RUN_START}>New run</Button>
          </>
        }
      />
    </div>
  );
}

const BAR = "rounded-ds-xs bg-surface-subtle";

/** The static skeleton of a run still loading (States mock, "Any run page"): nothing moves. */
function RunSkeleton() {
  const metric = (title: string, value: string, note: string) => (
    <div className="flex flex-col gap-2 rounded-xl border border-border-subtle bg-surface-card p-5 shadow-xs">
      <div className={cx(BAR, "h-3.5", title)} />
      <div className={cx(BAR, "h-9.5", value)} />
      <div className={cx(BAR, "h-3.5", note)} />
    </div>
  );
  const item = (title: string, text: string) => (
    <div className="flex items-start gap-4 rounded-lg border border-border-hairline bg-surface-card p-4">
      <div className={cx(BAR, "h-3.5 w-5 flex-none")} />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className={cx(BAR, "h-3.5", title)} />
        <div className={cx(BAR, "h-3.5", text)} />
      </div>
    </div>
  );
  return (
    <div aria-busy="true" className="flex flex-col gap-6">
      <div className={cx(BAR, "h-33 rounded-[10px]")} />
      <div className="grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-4">
        {metric("w-1/2", "w-[70%]", "w-4/5")}
        {metric("w-1/2", "w-3/5", "w-[70%]")}
        {metric("w-1/2", "w-[70%]", "w-3/5")}
      </div>
      <div className="flex flex-col gap-2.5">
        {item("w-[30%]", "w-[85%]")}
        {item("w-[36%]", "w-[70%]")}
      </div>
    </div>
  );
}

/**
 * Wraps every run page: the run header, the Show sources switch, the run tabs, and the trace
 * drawer that a page's trace controls open. `children` is the page body, or a function of the run
 * when the body reads the run's own record; a run still loading draws the skeleton in its place
 * and the function is not called.
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
  children: ReactNode | ((run: LoadedRun, issuer: string) => ReactNode);
}) {
  const [sources, setSources] = useSourcesOn();
  const [drawer, setDrawer] = useState<{ key: string | null; open: boolean }>({
    key: null,
    open: false,
  });
  return (
    <LibraryPage title={PAGE_NAME[tab]}>
      {({ issuers }) => {
        const issuer = issuers.find((item) => item.id === issuerId);
        if (issuer === undefined) {
          return (
            <NotHeld
              page={PAGE_NAME[tab]}
              title="No such issuer"
              description="The library holds no issuer at this address."
            />
          );
        }
        const run = issuer.runs.find((item) => item.id === runId);
        if (run === undefined) {
          return (
            <NotHeld
              page={PAGE_NAME[tab]}
              title="No such run"
              description="This issuer has no run at this address."
            />
          );
        }
        const trace =
          drawer.key !== null && Object.hasOwn(run.traces, drawer.key)
            ? run.traces[drawer.key]
            : undefined;
        return (
          <RunContext.Provider
            value={{
              traces: run.traces,
              open: (key) => {
                setDrawer({ key, open: true });
              },
            }}
          >
            <div data-sources={sources ? "on" : "off"} className="flex flex-col gap-8">
              <div className="flex flex-col gap-5">
                <RunHeader
                  issuer={issuer.id}
                  head={run.head}
                  sources={<SourcesSwitch isSelected={sources} onChange={setSources} />}
                />
                <RunTabs issuer={issuer.id} run={run} tab={tab} />
              </div>
              {run.loading ? (
                <RunSkeleton />
              ) : typeof children === "function" ? (
                children(run, issuer.id)
              ) : (
                children
              )}
            </div>
            {trace === undefined ? null : (
              <TraceDrawer
                trace={trace}
                evidenceHref={traceItemHref(issuer.id, run.id, trace.evidenceItem)}
                isOpen={drawer.open}
                onClose={() => {
                  setDrawer({ key: drawer.key, open: false });
                }}
              />
            )}
          </RunContext.Provider>
        );
      }}
    </LibraryPage>
  );
}
