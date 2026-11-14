import { Link } from "react-aria-components";
import { Badge } from "@/components/base/badges/badges";
import { ProgressBar } from "@/components/base/progress-indicators/progress-indicators";
import { Skeleton } from "@/components/gap/Skeleton";
import { StatusBadge } from "@/components/status/StatusBadge";
import type { IssuerCard as IssuerCardData } from "../slice";
import { cardHref } from "./links";

const CARD =
  "flex min-w-0 flex-col gap-5 rounded-ds-lg border border-border-subtle bg-surface-card p-8 shadow-1 text-text-primary";

/** An issuer and its latest run: header, lead, optional note, then as-of, pathway and progress. */
export function IssuerCard({ card }: { card: IssuerCardData }) {
  return (
    <Link
      href={cardHref(card.issuer, card.href)}
      className={`${CARD} no-underline outline-none transition-colors duration-150 hover:border-action-subtle-hover focus-visible:ring-2 focus-visible:ring-brand motion-reduce:transition-none`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-display text-h3 text-text-primary">{card.name}</h2>
          <span className="text-small text-text-tertiary">{card.sector}</span>
        </div>
        <StatusBadge set="Run states" state={card.state} />
      </div>
      <p className="text-body text-text-primary">{card.lead}</p>
      {card.note === null ? null : <p className="text-small text-text-secondary">{card.note}</p>}
      <div className="mt-auto flex flex-col gap-3.5 border-t border-border-hairline pt-5">
        <div className="flex flex-wrap gap-2">
          <Badge size="sm">{card.asOf}</Badge>
          <Badge size="sm">{card.pathway}</Badge>
        </div>
        <ProgressBar
          value={card.progress.value}
          max={card.progress.max}
          label={card.progress.text}
        />
      </div>
    </Link>
  );
}

/** A card whose issuer has not arrived: static blocks in its shape, marked busy. */
export function LoadingCard() {
  return (
    <div role="group" aria-busy="true" aria-label="Loading issuer" className={CARD}>
      <Skeleton lines={1} />
      <Skeleton lines={3} />
      <div className="mt-auto border-t border-border-hairline pt-5">
        <Skeleton lines={1} />
      </div>
    </div>
  );
}
