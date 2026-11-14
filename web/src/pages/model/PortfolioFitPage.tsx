import { PairTile } from "@/components/chart/PairTile";
import { Blocked } from "@/components/gap/Blocked";
import { PORTFOLIO_FIT_LABEL } from "./parts/ModelShell";
import { RunPage, runKey } from "./parts/RunPage";
import { LimitsCard, ScatterCard, StripsCard } from "./sections/PortfolioCharts";
import { SectionHeading, chartTrace, pairGrid } from "./sections/shared";
import type { PortfolioFitPage as PortfolioFit, RatingTile } from "./slice/types";

function entry({ label, value, caption }: RatingTile) {
  return { label, value, ...(caption === null ? {} : { caption }) };
}

function Ratings({ data }: { data: PortfolioFit["ratings"] }) {
  const [first, second] = data.tiles;
  return (
    <section className="group/trace flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <SectionHeading as="h3">{data.title}</SectionHeading>
        {chartTrace(data.trace, data.title)}
      </div>
      <PairTile tiles={[entry(first), entry(second)]} />
    </section>
  );
}

/** The part that failed in this run, drawn where its content would have been. */
function RelativeValue({ data }: { data: PortfolioFit["relativeValue"] }) {
  return (
    <section className="flex flex-col gap-4">
      <SectionHeading as="h3">{data.title}</SectionHeading>
      <div className="flex flex-col gap-2">
        <p className="font-medium text-text-primary">{data.part}</p>
        <Blocked reason={data.reason} />
      </div>
    </section>
  );
}

function Body({ page }: { page: PortfolioFit }) {
  const holdings = Math.max(page.scatter.head.length, page.strips.head.length);
  return (
    <div className="flex flex-col gap-10">
      <h2 className="sr-only">{PORTFOLIO_FIT_LABEL}</h2>
      <div className={pairGrid(page.limits.head.length)}>
        <LimitsCard data={page.limits} />
        <div className="flex min-w-0 flex-col gap-6">
          <Ratings data={page.ratings} />
          <RelativeValue data={page.relativeValue} />
        </div>
      </div>
      <div className={pairGrid(holdings)}>
        <ScatterCard data={page.scatter} />
        <StripsCard data={page.strips} />
      </div>
    </div>
  );
}

export function PortfolioFitPage({ params }: { params: Record<string, string> }) {
  return (
    <RunPage params={params} current="portfolio-fit">
      {(run) => <Body key={runKey(run)} page={run.portfolioFit} />}
    </RunPage>
  );
}
