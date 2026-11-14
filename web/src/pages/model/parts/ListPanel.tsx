import type { ReactNode } from "react";

export type ListPanelItem = {
  /** The delivered marker, for example "01". */
  number: string;
  lead: string;
  text: string;
  trace: ReactNode;
};

/**
 * A numbered list of findings on the canvas: the marker, a bold lead and its body, one trace
 * control each. Kit need: the kit's list panel has no marker column or trace control.
 */
export function ListPanel({ label, items }: { label: string; items: ListPanelItem[] }) {
  return (
    <ol aria-label={label} className="flex flex-col gap-2">
      {items.map((item) => (
        <li
          key={item.number}
          className="group/trace grid grid-cols-[28px_1fr_auto] items-start gap-2 rounded-ds-md border border-border-hairline bg-surface-card px-4 py-3"
        >
          <span className="text-caption leading-[22px] font-medium text-text-tertiary tabular-nums">
            {item.number}
          </span>
          <div className="min-w-0">
            <b className="block text-body leading-[26px] font-semibold text-text-primary">
              {item.lead}
            </b>
            <p className="max-w-[80ch] text-body text-text-secondary">{item.text}</p>
          </div>
          {item.trace}
        </li>
      ))}
    </ol>
  );
}
