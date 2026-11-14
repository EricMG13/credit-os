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
  /** Live run state: the half-filled action shape pulses a halo. */
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
  return <ToneBadge shape={found.shape} tone={found.tone} word={found.word} live={live} />;
}

interface ToneBadgeProps extends State {
  live?: boolean;
}

/** One badge from a shape, tone and word: the form every status and the gap badge share. */
export function ToneBadge({ shape, tone, word, live = false }: ToneBadgeProps) {
  const halo = live && shape === "half-filled circle" && tone === "action";
  return (
    <Badge
      color={BADGE_COLOUR[tone]}
      className="gap-1.5 pl-2"
      icon={
        <span className={cx("inline-flex rounded-ds-full", MARK[tone], halo && "status-halo")}>
          <StatusShape shape={shape} />
        </span>
      }
    >
      {word}
    </Badge>
  );
}
