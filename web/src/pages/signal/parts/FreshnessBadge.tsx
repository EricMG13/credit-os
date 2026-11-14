// The freshness line as a status badge. Shapes and tones come from the kit's "Freshness" set (and
// the Status set's Warning); the words are the delivered ones, which the kit's StatusBadge cannot
// carry (it draws only the set's own word). Nothing animates, including while checking.
import { Badge } from "@/components/base/badges/badges";
import type { BadgeColors } from "@/components/base/badges/badge-types";
import { STATUS_SETS, type State, type Tone } from "@/components/status/sets";
import { StatusShape } from "@/components/status/shapes";
import { cx } from "@/utils/cx";
import type { SignalFreshness } from "../slice";

const COLOUR: Partial<Record<Tone, BadgeColors>> = {
  success: "success",
  warning: "warning",
  neutral: "gray",
};
const MARK: Partial<Record<Tone, string>> = {
  success: "text-success-mark",
  warning: "text-warning-mark",
};

function look(freshness: SignalFreshness): State {
  const { Checked, "Not checked yet": NotChecked } = STATUS_SETS.Freshness;
  const problem = freshness.failing !== null || freshness.error !== null;
  switch (freshness.state) {
    case "checked":
      return problem ? STATUS_SETS.Status.Warning : Checked;
    case "checking":
    case "not-checked":
      return NotChecked;
    case "unavailable":
      return STATUS_SETS.Status.Warning;
  }
}

/** The delivered text: "Sources checked <time>", then each delivered suffix after " · ". */
function words(freshness: SignalFreshness): string {
  switch (freshness.state) {
    case "checking":
      return "Checking sources";
    case "not-checked":
      return "Sources not checked yet";
    case "unavailable":
      return "Source status unavailable";
    case "checked":
      if (freshness.checked === null) {
        throw new Error("the slice reader let through checked sources with no time");
      }
      return [`Sources checked ${freshness.checked}`, freshness.failing, freshness.error]
        .filter((part) => part !== null)
        .join(" · ");
  }
}

export function FreshnessBadge({ freshness }: { freshness: SignalFreshness }) {
  const { shape, tone } = look(freshness);
  return (
    <Badge
      color={COLOUR[tone] ?? "gray"}
      className="gap-1.5 pl-2"
      icon={
        <span className={cx("inline-flex rounded-ds-full", MARK[tone])}>
          <StatusShape shape={shape} />
        </span>
      }
    >
      {words(freshness)}
    </Badge>
  );
}
