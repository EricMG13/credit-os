import { Badge } from "@/components/base/badges/badges";
import type { BadgeColors } from "@/components/base/badges/badge-types";
import { cx } from "@/utils/cx";
import { STATUS_SETS, type SetName, type State, type Tone } from "./sets";
import { StatusShape } from "./shapes";

const BADGE_COLOUR: Record<Tone, BadgeColors> = {
  success: "success",
  warning: "warning",
  error: "error",
  info: "sky",
  neutral: "gray",
  action: "brand",
  gap: "gap",
};

// The four statuses mark their shape in the mark colour; other tones keep the text colour.
const MARK: Partial<Record<Tone, string>> = {
  success: "text-success-mark",
  warning: "text-warning-mark",
  error: "text-error-mark",
  info: "text-info-mark",
};

interface StatusBadgeProps<S extends SetName> {
  set: S;
  state: keyof (typeof STATUS_SETS)[S] & string;
  /** Live run state: only the Run states set's Running badge pulses a halo. */
  live?: boolean;
}

export function StatusBadge<S extends SetName>({ set, state, live = false }: StatusBadgeProps<S>) {
  const states: Readonly<Record<string, State | undefined>> | undefined = Object.hasOwn(
    STATUS_SETS,
    set,
  )
    ? STATUS_SETS[set]
    : undefined;
  const found = states !== undefined && Object.hasOwn(states, state) ? states[state] : undefined;
  if (found === undefined) throw new Error(`unknown status state "${state}" in set "${set}"`);
  return (
    <ToneBadge
      shape={found.shape}
      tone={found.tone}
      word={found.word}
      live={live && set === "Run states" && state === "Running"}
    />
  );
}

interface ToneBadgeProps extends State {
  /** Draw the pulsing halo; the caller has already decided this is the live Running badge. */
  live?: boolean;
}

/** One badge from a shape, tone and word. Private: callers go through the checked sets. */
function ToneBadge({ shape, tone, word, live = false }: ToneBadgeProps) {
  return (
    <Badge
      color={BADGE_COLOUR[tone]}
      className="gap-1.5 pl-2"
      icon={
        <span className={cx("inline-flex rounded-ds-full", MARK[tone], live && "status-halo")}>
          <StatusShape shape={shape} />
        </span>
      }
    >
      {word}
    </Badge>
  );
}

/** The inline form of a gap, for a table cell or a chart. */
export function GapBadge() {
  return <ToneBadge shape="dashed ring" tone="gap" word="Not established for this run" />;
}
