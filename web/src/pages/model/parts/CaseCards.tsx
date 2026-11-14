import { useId } from "react";
import { cx } from "@/utils/cx";
import type { CaseCard } from "../slice/types";
import { TraceControl } from "./TraceControl";

/**
 * The case choice: a radio group of cards. The chosen case is the caller's state. The trace
 * control sits beside the card's label, not inside it, so pressing it never changes the case.
 * Kit need: a choice card (the kit has no radio card or choicebox).
 */
export function CaseCards({
  cases,
  chosen,
  onChoose,
}: {
  cases: readonly CaseCard[];
  chosen: number;
  onChoose: (index: number) => void;
}) {
  const group = useId();
  return (
    <div
      role="radiogroup"
      aria-label="Case"
      className="grid grid-cols-[repeat(auto-fit,minmax(320px,1fr))] gap-4"
    >
      {cases.map((card, index) => (
        <Card
          key={index}
          card={card}
          name={group}
          checked={index === chosen}
          onChoose={() => {
            onChoose(index);
          }}
        />
      ))}
    </div>
  );
}

function Card({
  card,
  name,
  checked,
  onChoose,
}: {
  card: CaseCard;
  name: string;
  checked: boolean;
  onChoose: () => void;
}) {
  const id = useId();
  return (
    <div data-case className="flex flex-col gap-2">
      <div className="group/trace relative">
        <label
          className={cx(
            "relative block cursor-pointer rounded-ds-md border bg-surface-card px-3 py-2.5 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-focus",
            checked ? "border-action bg-surface-selected" : "border-border-hairline",
          )}
        >
          <input
            type="radio"
            name={name}
            checked={checked}
            onChange={onChoose}
            aria-labelledby={`${id}-name`}
            aria-describedby={`${id}-tag ${id}-assumption ${id}-leaves`}
            className="sr-only"
          />
          <span className="flex items-baseline gap-2 text-sm font-semibold text-text-primary">
            <span id={`${id}-name`}>{card.name}</span>
            <span id={`${id}-tag`} className="text-caption font-normal text-text-tertiary">
              {card.tag}
            </span>
            <span
              aria-hidden="true"
              className={cx(
                "ml-auto size-4 flex-none self-center rounded-full border",
                checked ? "border-5 border-action" : "border-border-control",
              )}
            />
          </span>
          <p id={`${id}-assumption`} className="mt-0.5 pr-7 text-sm text-text-secondary">
            {card.assumption}
          </p>
          <p id={`${id}-leaves`} className="mt-0.5 pr-11 text-sm text-text-tertiary">
            Leaves out: {card.leavesOut}
          </p>
        </label>
        {card.trace === null ? null : (
          <div className="absolute right-2.5 bottom-2.5">
            <TraceControl href={card.trace} label={`Show the sources for ${card.name}`} />
          </div>
        )}
      </div>
      {card.note === null ? null : <p className="text-small text-text-tertiary">{card.note}</p>}
    </div>
  );
}
