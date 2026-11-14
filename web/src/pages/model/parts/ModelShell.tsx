import type { ReactNode } from "react";
import { ArrowUpRight } from "@untitledui/icons";
import { Badge } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { StatusBadge } from "@/components/status/StatusBadge";
import { PageHeader } from "@/shell/PageHeader";
import { cx } from "@/utils/cx";
import type { ModelRun } from "../slice/types";
import { ShowSources, ShowSourcesSwitch } from "./ShowSources";

/** The Portfolio fit tab's label; the page's hidden heading takes its text from here. */
export const PORTFOLIO_FIT_LABEL = "Portfolio fit";

const TABS = [
  ["front", "Front page"],
  ["analysis", "Analysis"],
  ["statements", "Model"],
  ["portfolio-fit", PORTFOLIO_FIT_LABEL],
  ["limitations", "Limitations"],
] as const;

type ModelPage = (typeof TABS)[number][0];

export type ShellPage = ModelPage;

const COUNT =
  "rounded-full border border-border-hairline bg-surface-subtle px-2 text-caption text-text-secondary";

const TAB =
  "flex items-center gap-2 -mb-px border-b-2 px-1 pb-3 text-sm font-semibold outline-focus focus-visible:outline-2 focus-visible:outline-offset-2";

/** What a Model page draws inside the app's main: breadcrumb, switch, header, tabs, then the page. */
export function ModelShell({
  run,
  current,
  children,
}: {
  run: ModelRun;
  current: ShellPage;
  children: ReactNode;
}) {
  const base = `#/model/${encodeURIComponent(run.issuer)}/${encodeURIComponent(run.run)}`;
  const { header, links } = run;
  return (
    <ShowSources>
      <div className="flex flex-col gap-5 p-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <nav aria-label="Breadcrumb">
            <ol className="flex items-center gap-2 text-sm font-semibold text-text-tertiary">
              <li>
                <a href={links.library}>Library</a>
              </li>
              <li aria-hidden="true">/</li>
              <li>
                <a href={links.report}>{header.issuerName}</a>
              </li>
              <li aria-hidden="true">/</li>
              <li aria-current="page" className="text-text-primary">
                Financial model
              </li>
            </ol>
          </nav>
          <ShowSourcesSwitch />
        </div>
        <PageHeader
          as="h1"
          title={header.issuerName}
          badges={
            <>
              <Badge>{header.asOf}</Badge>
              <Badge>{header.purpose}</Badge>
              <StatusBadge set="Run states" state={header.state} />
              {header.sample ? <Badge>Sample data</Badge> : null}
            </>
          }
          actions={
            <Button href={links.report} size="md" color="secondary">
              Back to the report
            </Button>
          }
        />
        <nav aria-label="Pages" className="flex flex-wrap gap-4 border-b border-border-hairline">
          <>
            {TABS.map(([key, label]) => (
              <a
                key={key}
                href={`${base}/${key}`}
                aria-current={key === current ? "page" : undefined}
                className={cx(
                  TAB,
                  key === current
                    ? "border-action text-action"
                    : "border-transparent text-text-tertiary",
                )}
              >
                {label}
                {key === "limitations" ? (
                  <span className={COUNT}>{run.limitations.count}</span>
                ) : null}
              </a>
            ))}
            <a
              href={links.evidence}
              className={cx(TAB, "ml-auto border-transparent text-text-tertiary")}
            >
              Evidence
              <ArrowUpRight className="size-4" aria-hidden="true" />
            </a>
          </>
        </nav>
        {children}
      </div>
    </ShowSources>
  );
}
