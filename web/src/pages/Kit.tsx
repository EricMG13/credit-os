import type { ReactNode } from "react";
import { AlertCircle, CheckCircle, InfoCircle, SearchLg, Server01 } from "@untitledui/icons";
import type { IconProps } from "@/utils/is-react-component";
import { Alert, Callout } from "@/components/alert/Alert";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { Tab, TabList, TabPanel, Tabs } from "@/components/application/tabs/tabs";
import { Badge, BadgeWithDot } from "@/components/base/badges/badges";
import { ButtonGroup, ButtonGroupItem } from "@/components/base/button-group/button-group";
import { Button, styles } from "@/components/base/buttons/button";
import { Tooltip, TooltipTrigger } from "@/components/base/tooltip/tooltip";
import { TrendChart } from "@/components/chart/TrendChart";
import { Card, Tile } from "@/components/card/Card";
import { Blocked } from "@/components/gap/Blocked";
import { GapPanel } from "@/components/gap/GapPanel";
import { Missing } from "@/components/gap/Missing";
import { Skeleton } from "@/components/gap/Skeleton";
import { Withheld } from "@/components/gap/Withheld";
import { MetricCard } from "@/components/metric/MetricCard";
import { Timeline } from "@/components/timeline/Timeline";
import { PageHeader } from "@/shell/PageHeader";
import { STATUS_SETS, type SetName } from "@/components/status/sets";
import { GapBadge, StatusBadge } from "@/components/status/StatusBadge";

function label(slug: string): string {
  const words = slug.replace("-", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

const BADGE_COLOURS = ["gray", "brand", "error", "warning", "success", "sky"] as const;
const BADGE_SIZES = ["sm", "md", "lg"] as const;

function Plus({ className, "data-icon": slot }: IconProps) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      aria-hidden="true"
      data-icon={slot}
      className={className}
    >
      <path d="M10 4v12M4 10h12" />
    </svg>
  );
}

const FEATURED = [
  { colour: "brand", icon: InfoCircle },
  { colour: "gray", icon: SearchLg },
  { colour: "error", icon: AlertCircle },
  { colour: "warning", icon: AlertCircle },
  { colour: "success", icon: CheckCircle },
] as const;

const PERIODS = ["FY21", "FY22", "FY23", "FY24", "FY25", "FY26"];

// Sample data, written out: the page computes and formats no figure.
const TREND = {
  series: [
    { name: "Net debt", values: [412, 398, 377, 361, 340, 322] },
    { name: "Gross debt", values: [520, 511, null, 478, 455, 431] },
    { name: "Cash", values: [108, 113, 118, 117, 115, 109] },
  ],
  table: [
    { name: "Net debt", cells: ["412", "398", "377", "361", "340", "322"] },
    { name: "Gross debt", cells: ["520", "511", null, "478", "455", "431"] },
    { name: "Cash", cells: ["108", "113", "118", "117", "115", "109"] },
  ],
};

const FOLDED = {
  series: [
    { name: "Term loan", values: [10, 13, 16, 19, 22, 25] },
    { name: "Notes", values: [20, 23, 26, 29, 32, 35] },
    { name: "Revolver", values: [30, 33, 36, 39, 42, 45] },
    { name: "Leases", values: [40, 43, 46, 49, 52, 55] },
    { name: "Pensions", values: [50, 53, 56, 59, 62, 65] },
    { name: "Overdraft", values: [60, 63, 66, 69, 72, 75] },
    { name: "Bonds", values: [70, 73, 76, 79, 82, 85] },
    { name: "Other debt", values: [80, 83, 86, 89, 92, 95] },
  ],
  table: [
    { name: "Term loan", cells: ["10", "13", "16", "19", "22", "25"] },
    { name: "Notes", cells: ["20", "23", "26", "29", "32", "35"] },
    { name: "Revolver", cells: ["30", "33", "36", "39", "42", "45"] },
    { name: "Leases", cells: ["40", "43", "46", "49", "52", "55"] },
    { name: "Pensions", cells: ["50", "53", "56", "59", "62", "65"] },
    { name: "Overdraft", cells: ["60", "63", "66", "69", "72", "75"] },
    { name: "Bonds", cells: ["70", "73", "76", "79", "82", "85"] },
    { name: "Other debt", cells: ["80", "83", "86", "89", "92", "95"] },
  ],
};

const TREND_TICKS = [
  { value: 0, label: "0" },
  { value: 200, label: "200" },
  { value: 400, label: "400" },
  { value: 600, label: "600" },
];
const FOLDED_TICKS = [
  { value: 0, label: "0" },
  { value: 50, label: "50" },
  { value: 100, label: "100" },
];

function Row({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap items-center gap-4">{children}</div>;
}

export function Kit() {
  const colours = Object.keys(styles.colors) as (keyof typeof styles.colors)[];
  const sizes = Object.keys(styles.sizes) as (keyof typeof styles.sizes)[];
  return (
    <div className="text-text-primary">
      <PageHeader title="Component kit" />

      <section className="mt-8 flex flex-col gap-4">
        <h2 className="font-display text-h2 text-text-primary">Button</h2>
        <Row>
          {colours.map((colour) => (
            <Button key={colour} color={colour} size="md">
              {label(colour)}
            </Button>
          ))}
        </Row>
        <Row>
          {sizes.map((size) => (
            <Button key={size} size={size}>
              {`Size ${size}`}
            </Button>
          ))}
        </Row>
        <Row>
          <Button isDisabled>Disabled</Button>
          <Button isLoading>Loading</Button>
          <Button iconLeading={Plus}>Leading icon</Button>
          <Button iconTrailing={Plus}>Trailing icon</Button>
        </Row>
      </section>

      <section className="mt-8 flex flex-col gap-4">
        <h2 className="font-display text-h2 text-text-primary">Tooltip</h2>
        <Row>
          <Tooltip title="Tooltip title" description="Supporting text under the title.">
            <TooltipTrigger className="text-small text-text-link focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus">
              Tooltip trigger
            </TooltipTrigger>
          </Tooltip>
        </Row>
      </section>

      <section aria-labelledby="kit-badge" className="mt-8 flex flex-col gap-4">
        <h2 id="kit-badge" className="font-display text-h2 text-text-primary">
          Badge
        </h2>
        <Row>
          {BADGE_COLOURS.map((colour) => (
            <Badge key={colour} color={colour}>
              {label(colour)}
            </Badge>
          ))}
        </Row>
        <Row>
          {BADGE_COLOURS.map((colour) => (
            <BadgeWithDot key={colour} color={colour}>
              {label(colour)}
            </BadgeWithDot>
          ))}
        </Row>
        <Row>
          {BADGE_SIZES.map((size) => (
            <Badge key={size} size={size}>
              {`Size ${size}`}
            </Badge>
          ))}
        </Row>
      </section>

      <section aria-labelledby="kit-status-badge" className="mt-8 flex flex-col gap-4">
        <h2 id="kit-status-badge" className="font-display text-h2 text-text-primary">
          Status badge
        </h2>
        {(Object.keys(STATUS_SETS) as SetName[]).map((name) => (
          <div key={name} className="flex flex-col gap-2">
            <h3 className="font-display text-h4 text-text-primary">{name}</h3>
            <Row>
              {Object.keys(STATUS_SETS[name]).map((state) => (
                <StatusBadge key={state} set={name as "Status"} state={state as "Success"} />
              ))}
            </Row>
          </div>
        ))}
        <div role="group" aria-label="Live run state" className="flex flex-col gap-3">
          <h3 className="font-display text-h4 text-text-primary">Live run state</h3>
          <Row>
            <StatusBadge set="Run states" state="Running" live />
          </Row>
          <div className="queued-shimmer w-64" />
        </div>
      </section>

      <section aria-labelledby="kit-tabs" className="mt-8 flex flex-col gap-4">
        <h2 id="kit-tabs" className="font-display text-h2 text-text-primary">
          Tabs
        </h2>
        <Tabs>
          <TabList type="underline" aria-label="Horizontal tabs">
            <Tab id="overview">Overview</Tab>
            <Tab id="changes" badge="12">
              Changes
            </Tab>
            <Tab id="evidence">Evidence</Tab>
          </TabList>
          <TabPanel id="overview" className="pt-4 text-body">
            Overview panel
          </TabPanel>
          <TabPanel id="changes" className="pt-4 text-body">
            Changes panel
          </TabPanel>
          <TabPanel id="evidence" className="pt-4 text-body">
            Evidence panel
          </TabPanel>
        </Tabs>
        <Tabs orientation="vertical" className="flex-row gap-6">
          <TabList type="line" aria-label="Vertical tabs">
            <Tab id="sources">Sources</Tab>
            <Tab id="modules">Modules</Tab>
            <Tab id="forecast">Forecast</Tab>
          </TabList>
          <TabPanel id="sources" className="text-body">
            Sources panel
          </TabPanel>
          <TabPanel id="modules" className="text-body">
            Modules panel
          </TabPanel>
          <TabPanel id="forecast" className="text-body">
            Forecast panel
          </TabPanel>
        </Tabs>
      </section>

      <section aria-labelledby="kit-button-group" className="mt-8 flex flex-col gap-4">
        <h2 id="kit-button-group" className="font-display text-h2 text-text-primary">
          Button group
        </h2>
        <Row>
          <ButtonGroup aria-label="Chart or Table" defaultSelectedKeys={["chart"]}>
            <ButtonGroupItem id="chart">Chart</ButtonGroupItem>
            <ButtonGroupItem id="table">Table</ButtonGroupItem>
          </ButtonGroup>
        </Row>
      </section>

      <section aria-labelledby="kit-card" className="mt-8 flex flex-col gap-4">
        <h2 id="kit-card" className="font-display text-h2 text-text-primary">
          Card and tile
        </h2>
        <Card title="Card with a title">
          <p className="text-body text-text-secondary">Card content, with a shadow.</p>
        </Card>
        <Tile>Tile content</Tile>
      </section>

      <section aria-labelledby="kit-metric" className="mt-8 flex flex-col gap-4">
        <h2 id="kit-metric" className="font-display text-h2 text-text-primary">
          Metric card
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <MetricCard label="Net leverage" value="4.2x" note="Net debt over EBITDA." />
          <MetricCard label="Revenue" value="1,204" from="1,150" />
          <MetricCard label="Interest cover" value={null} />
        </div>
      </section>

      <section aria-labelledby="kit-timeline" className="mt-8 flex flex-col gap-4">
        <h2 id="kit-timeline" className="font-display text-h2 text-text-primary">
          Timeline
        </h2>
        <Timeline
          items={[
            { date: "12 Feb 2025", title: "Annual report filed", text: "Filed.", state: "Past" },
            { date: "15 Mar 2026", title: "Covenant test", state: "Next" },
            { date: "24 Apr 2027", title: "Notes mature", state: "Later" },
          ]}
        />
      </section>

      <section aria-labelledby="kit-featured-icon" className="mt-8 flex flex-col gap-4">
        <h2 id="kit-featured-icon" className="font-display text-h2 text-text-primary">
          Featured icon
        </h2>
        <Row>
          {FEATURED.map(({ colour, icon }) => (
            <div key={colour} className="flex flex-col items-center gap-2">
              <FeaturedIcon color={colour} icon={icon} />
              <span className="text-small text-text-secondary">{label(colour)}</span>
            </div>
          ))}
        </Row>
      </section>

      <section aria-labelledby="kit-empty-state" className="mt-8 flex flex-col gap-4">
        <h2 id="kit-empty-state" className="font-display text-h2 text-text-primary">
          Empty state
        </h2>
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
          <EmptyState>
            <EmptyState.Header>
              <EmptyState.FeaturedIcon icon={SearchLg} />
            </EmptyState.Header>
            <EmptyState.Content>
              <EmptyState.Title as="h3">No changes yet</EmptyState.Title>
              <EmptyState.Description>
                Changes appear here once a second run has finished.
              </EmptyState.Description>
            </EmptyState.Content>
          </EmptyState>
          <EmptyState>
            <EmptyState.Header>
              <EmptyState.FeaturedIcon icon={Server01} />
            </EmptyState.Header>
            <EmptyState.Content>
              <EmptyState.Title as="h3">No sources yet</EmptyState.Title>
              <EmptyState.Description>
                Add the issuer files to start the first run.
              </EmptyState.Description>
            </EmptyState.Content>
            <EmptyState.Footer>
              <Button size="lg">Add sources</Button>
            </EmptyState.Footer>
          </EmptyState>
        </div>
      </section>

      <section aria-labelledby="kit-alert" className="mt-8 flex flex-col gap-4">
        <h2 id="kit-alert" className="font-display text-h2 text-text-primary">
          Alert
        </h2>
        <div className="flex max-w-md flex-col gap-4">
          <Alert tone="success" title="Success">
            The run finished and the library is ready.
          </Alert>
          <Alert tone="error" title="Error">
            The service could not be reached.
          </Alert>
          <Alert tone="warning" title="Warning">
            The run is close to its cost cap.
          </Alert>
          <Alert
            tone="info"
            title="Info"
            action={
              <Button size="sm" color="secondary">
                Open run
              </Button>
            }
          >
            The run has started.
          </Alert>
        </div>
      </section>

      <section aria-labelledby="kit-callout" className="mt-8 flex flex-col gap-4">
        <h2 id="kit-callout" className="font-display text-h2 text-text-primary">
          Callout
        </h2>
        <div className="max-w-xl">
          <Callout title="What would change the view">
            A covenant breach, or a refinancing that misses the next maturity.
          </Callout>
        </div>
      </section>

      <section aria-labelledby="kit-trend-chart" className="mt-8 flex flex-col gap-6">
        <h2 id="kit-trend-chart" className="font-display text-h2 text-text-primary">
          Trend chart
        </h2>
        <TrendChart
          title="Debt by period"
          note="Sample figures in millions. Gross debt is missing for FY23."
          periods={PERIODS}
          series={TREND.series}
          table={TREND.table}
          yTicks={TREND_TICKS}
        />
        <TrendChart
          title="Eight series"
          note="The seventh and later series take the Other style."
          periods={PERIODS}
          series={FOLDED.series}
          table={FOLDED.table}
          yTicks={FOLDED_TICKS}
        />
      </section>

      <section aria-labelledby="kit-gap-states" className="mt-8 flex flex-col gap-4">
        <h2 id="kit-gap-states" className="font-display text-h2 text-text-primary">
          Gap states
        </h2>
        <GapPanel reason="No filing in the sources covers this period." />
        <Row>
          <GapBadge />
        </Row>
        <Row>
          <Missing />
        </Row>
        <Withheld reason="The issuer has not released this figure." />
        <Blocked reason="The cash-flow statement is missing from the sources." />
        <div className="w-64">
          <Skeleton lines={3} />
        </div>
      </section>

      <section aria-labelledby="kit-page-header" className="mt-8 flex flex-col gap-4">
        <h2 id="kit-page-header" className="font-display text-h2 text-text-primary">
          Page header
        </h2>
        <PageHeader
          as="h3"
          title="Issuer name"
          badges={
            <>
              <Badge color="gray">As of 31 Dec 2025</Badge>
              <BadgeWithDot color="success">Complete</BadgeWithDot>
            </>
          }
          actions={<Button color="secondary">Action</Button>}
        />
      </section>
    </div>
  );
}
