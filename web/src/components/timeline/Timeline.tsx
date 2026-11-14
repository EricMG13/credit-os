// Follows the HyperUI timeline "Vertical": a rule down the left, a marker and text per item.
import { StatusBadge } from "@/components/status/StatusBadge";
import { STATUS_SETS } from "@/components/status/sets";
import { StatusShape } from "@/components/status/shapes";

type DatedState = keyof (typeof STATUS_SETS)["Dated records"];

interface TimelineItem {
  date: string;
  title: string;
  text?: string;
  state: DatedState;
}

export function Timeline({ items }: { items: readonly TimelineItem[] }) {
  return (
    <ol className="relative space-y-8 before:absolute before:-ms-px before:h-full before:w-0.5 before:rounded-full before:bg-connector">
      {items.map((item) => {
        const { shape, tone } = STATUS_SETS["Dated records"][item.state];
        return (
          <li
            key={`${item.date}-${item.title}`}
            className="relative -ms-1.5 flex items-start gap-4"
          >
            <span
              className={`mt-px shrink-0 rounded-ds-full bg-surface-canvas ${tone === "action" ? "text-action" : "text-text-tertiary"}`}
            >
              <StatusShape shape={shape} />
            </span>
            <div className="-mt-2 flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <time className="text-xs/none font-medium text-text-secondary">{item.date}</time>
                <StatusBadge set="Dated records" state={item.state} />
              </div>
              <h3 className="font-display text-h4 text-text-primary">{item.title}</h3>
              {item.text !== undefined && (
                <p className="text-sm text-text-secondary">{item.text}</p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
