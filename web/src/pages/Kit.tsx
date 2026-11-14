import type { ReactNode } from "react";
import type { IconProps } from "@/utils/is-react-component";
import { Tab, TabList, TabPanel, Tabs } from "@/components/application/tabs/tabs";
import { Badge, BadgeWithDot } from "@/components/base/badges/badges";
import { ButtonGroup, ButtonGroupItem } from "@/components/base/button-group/button-group";
import { Button, styles } from "@/components/base/buttons/button";
import { Tooltip, TooltipTrigger } from "@/components/base/tooltip/tooltip";
import { Blocked } from "@/components/gap/Blocked";
import { GapBadge, GapPanel } from "@/components/gap/GapPanel";
import { Missing } from "@/components/gap/Missing";
import { Skeleton } from "@/components/gap/Skeleton";
import { Withheld } from "@/components/gap/Withheld";
import { PageHeader } from "@/shell/PageHeader";
import { STATUS_SETS, type SetName } from "@/components/status/sets";
import { StatusBadge } from "@/components/status/StatusBadge";

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
          as="h2"
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
