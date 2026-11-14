import { ArrowUpRight } from "@untitledui/icons";
import { Link } from "react-aria-components";
import { Tooltip } from "@/components/base/tooltip/tooltip";
import { cx } from "@/utils/cx";
import { useShowSources } from "./ShowSources";

/**
 * An icon-only link to the sources of one item. It sits inside a `group/trace` row, tile or
 * passage, and shows when that is hovered or focused, under "Show sources" and on a touch device.
 * It is hidden by opacity, never removed, so Tab always reaches it.
 */
export function TraceControl({
  href,
  label,
  onInverse = false,
}: {
  href: string;
  label: string;
  /** On a Navy surface: the ring takes the inverse focus colour. */
  onInverse?: boolean;
}) {
  const shown = useShowSources();
  return (
    <Tooltip title="Show sources">
      <Link
        href={href}
        aria-label={label}
        className={cx(
          "inline-flex size-7 flex-none cursor-pointer items-center justify-center rounded-full border border-border-control bg-surface-card text-text-secondary focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-offset-2 hover:opacity-100 group-hover/trace:opacity-100 group-focus-within/trace:opacity-100 [@media(hover:none)]:opacity-100",
          onInverse ? "outline-focus-inverse" : "outline-focus",
          shown ? "opacity-100" : "opacity-0",
        )}
      >
        <ArrowUpRight className="size-4" aria-hidden="true" />
      </Link>
    </Tooltip>
  );
}
