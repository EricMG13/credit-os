import type { ReactNode } from "react";
import { StatusShape, type Shape } from "@/components/status/shapes";
import { cx } from "@/utils/cx";

// Tone classes written out whole so the class scan finds them.
const TONES = {
  warning: {
    shape: "triangle",
    box: "rounded-ds-md border border-warning-mark bg-warning-fill text-warning-text",
    mark: "text-warning-mark",
  },
  info: {
    shape: "ring",
    box: "border-s-4 border-info-mark bg-info-fill text-info-text",
    mark: "text-info-mark",
  },
} as const satisfies Record<string, { shape: Shape; box: string; mark: string }>;

/**
 * A standout passage on the canvas: a toned box with the tone's shape, the title and, at the end
 * of the title row, a trace control, then the body at the body size. It is a plain region named
 * by its title: never dismissible and never announced as an alert. Kit need: the kit's Alert and
 * Callout have no trace slot in the title row, set the body below `body`, and Alert is an alert.
 */
export function Passage({
  tone,
  title,
  trace,
  children,
}: {
  tone: keyof typeof TONES;
  title: string;
  trace: ReactNode;
  children: string;
}) {
  const t = TONES[tone];
  return (
    <section aria-label={title} className={cx("group/trace max-w-[90ch] p-4 shadow-sm", t.box)}>
      <div data-title-row="" className="flex items-start gap-2">
        <span
          aria-hidden="true"
          className={cx("flex size-6 flex-none items-center justify-center", t.mark)}
        >
          <StatusShape shape={t.shape} />
        </span>
        <strong className="min-w-0 flex-1 text-small font-medium">{title}</strong>
        {trace}
      </div>
      <p className="mt-1 ps-8 text-body">{children}</p>
    </section>
  );
}
