import { Button, styles } from "@/components/base/buttons/button";
import { Badge } from "@/components/base/badges/badges";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { LoadingIndicator } from "@/components/application/loading-indicator/loading-indicator";
import { Card } from "@/components/card/Card";
import { Skeleton } from "@/components/gap/Skeleton";
import { StatusBadge } from "@/components/status/StatusBadge";
import { PageHeader } from "@/shell/PageHeader";
import { cx } from "@/utils/cx";
import { useSource } from "../../source";
import { TextLink } from "../TextLink";
import { readSlice } from "../slice";
import type { StartDraft } from "../slice-start";
import type { ActivityRecord, RunRecord } from "../slice-activity";
import { Feed } from "./Feed";
import { RunAlert } from "./RunAlert";
import { ModuleSteps } from "./ModuleSteps";
import { Summary } from "./Summary";

const STOP_REASON =
  "Not available here: this page shows a saved example and is not connected to the run service.";

// The page draws its own padding (the shell gives a bleed page none) and its own h1.
function Frame({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-col gap-6 p-8">{children}</div>;
}

function Empty({
  title,
  trail = false,
  action,
  children,
}: {
  title: string;
  trail?: boolean;
  action?: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <Frame>
      {trail ? <span className="text-sm text-text-tertiary">Runs</span> : null}
      <PageHeader title="Run activity" />
      <EmptyState>
        <EmptyState.Header>
          <EmptyState.FeaturedIcon />
        </EmptyState.Header>
        <EmptyState.Content>
          <EmptyState.Title>{title}</EmptyState.Title>
          {children}
        </EmptyState.Content>
        {action === undefined ? null : <EmptyState.Footer>{action}</EmptyState.Footer>}
      </EmptyState>
    </Frame>
  );
}

function NoRun({ draft }: { draft: StartDraft | undefined }) {
  return (
    <Empty
      title="No run to watch"
      trail
      action={
        draft === undefined ? undefined : (
          <a
            href={`#/run/start/${draft.id}`}
            className={cx(styles.common.root, styles.sizes.lg.root, styles.colors.primary.root)}
          >
            <span data-text className="px-0.5">
              Start a run
            </span>
          </a>
        )
      }
    >
      <EmptyState.Description>
        Nothing is running and no run has been started here yet. A run appears on this page as soon
        as you submit it.
      </EmptyState.Description>
    </Empty>
  );
}

// The summary and the two panels, as static blocks: no figure is known.
function Unreadable({ run }: { run: Extract<ActivityRecord, { kind: "unreadable" }> }) {
  return (
    <Frame>
      <PageHeader
        title={run.issuer}
        badges={
          <>
            <StatusBadge set="Activity that cannot be read" state="State not known" />
            {run.labels.map((label, i) => (
              <Badge key={`${label}-${String(i)}`}>{label}</Badge>
            ))}
          </>
        }
      />
      <RunAlert state="unreadable" alert={run.alert} />
      <Card>
        <Skeleton lines={3} />
      </Card>
      <div className="grid items-start gap-6 min-[1101px]:grid-cols-[minmax(0,1fr)_400px]">
        <Card>
          <Skeleton lines={5} />
        </Card>
        <Card>
          <Skeleton lines={4} />
        </Card>
      </div>
    </Frame>
  );
}

function Modules({ run, live }: { run: RunRecord; live: boolean }) {
  const { modules } = run;
  return (
    <section aria-labelledby="run-modules" className="min-w-0">
      <Card>
        <h2 id="run-modules" className="mb-6 font-display text-h3 text-text-primary">
          Modules
        </h2>
        {modules.kind === "steps" ? <ModuleSteps steps={modules.steps} live={live} /> : null}
        {modules.kind === "starting" ? (
          <div className="py-12">
            <LoadingIndicator label={modules.label} />
          </div>
        ) : null}
        {modules.kind === "none" ? (
          <EmptyState>
            <EmptyState.Header>
              <EmptyState.FeaturedIcon />
            </EmptyState.Header>
            <EmptyState.Content>
              <EmptyState.Title as="h3">{modules.title}</EmptyState.Title>
              <EmptyState.Description>{modules.text}</EmptyState.Description>
            </EmptyState.Content>
          </EmptyState>
        ) : null}
      </Card>
    </section>
  );
}

function Run({ run }: { run: RunRecord }) {
  const live = run.state === "Queued" || run.state === "Running";
  return (
    <Frame>
      <nav aria-label="Breadcrumb" className="text-sm text-text-tertiary">
        <TextLink href="#/run">Runs</TextLink>
        {` / ${run.issuer}`}
      </nav>
      <PageHeader
        title={run.issuer}
        badges={
          <>
            <StatusBadge set="Run states" state={run.state} live={live} />
            {run.labels.map((label, i) => (
              <Badge key={`${label}-${String(i)}`}>{label}</Badge>
            ))}
          </>
        }
        actions={
          run.open !== null ? (
            <a
              href={run.open.href}
              className={cx(styles.common.root, styles.sizes.lg.root, styles.colors.primary.root)}
            >
              <span data-text className="px-0.5">
                {run.open.label}
              </span>
            </a>
          ) : live ? (
            <div className="flex max-w-xs flex-col items-start gap-2">
              <Button color="secondary" isDisabled aria-describedby="stop-reason">
                Stop run
              </Button>
              <span id="stop-reason" className="text-sm text-text-secondary">
                {STOP_REASON}
              </span>
            </div>
          ) : null
        }
      />
      {run.line === null ? null : (
        <p className="max-w-2xl text-body text-text-secondary">{run.line}</p>
      )}
      {run.alert === null ? null : <RunAlert state={run.state} alert={run.alert} />}
      <Summary run={run} />
      <div className="grid items-start gap-6 min-[1101px]:grid-cols-[minmax(0,1fr)_400px]">
        <Modules run={run} live={live} />
        <section aria-labelledby="run-feed" className="min-w-0">
          <Card>
            <h2 id="run-feed" className="mb-6 font-display text-h3 text-text-primary">
              Activity
            </h2>
            <Feed lines={run.feed} live={live} />
          </Card>
        </section>
      </div>
    </Frame>
  );
}

/** One run's activity: the run the address names, or (no id) the one the slice names as current. */
export function ActivityPage({ run: id }: { run: string | null }) {
  const slice = readSlice(useSource().run);
  if (slice.kind !== "ok") return <Empty title="No run data in this library" />;
  const wanted = id ?? slice.data.current;
  const record = slice.data.runs.find((r) => r.id === wanted);
  if (wanted === null) return <NoRun draft={slice.data.drafts[0]} />;
  if (record === undefined) {
    return (
      <Empty title="No run has this address">
        <TextLink href="#/run">Go to Run</TextLink>
      </Empty>
    );
  }
  if (record.kind === "none") return <NoRun draft={slice.data.drafts[0]} />;
  if (record.kind === "unreadable") return <Unreadable run={record} />;
  return <Run run={record} />;
}
