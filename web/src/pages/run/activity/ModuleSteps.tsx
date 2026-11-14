import { useEffect, useRef, useState } from "react";
import { Check } from "@untitledui/icons";
import { StatusBadge } from "@/components/status/StatusBadge";
import { cx } from "@/utils/cx";
import type { ModuleStep, ModuleWord } from "../slice-activity";
import "./activity.css";

type Row = {
  key: string;
  name: string;
  state: ModuleWord;
  detail: string | null;
  group: { index: number; showAll: string } | null;
  revealedFirst: boolean;
};

// An opened group is replaced by its modules; nothing is counted, every title is the slice's.
function rowsOf(steps: ModuleStep[], opened: ReadonlySet<number>, last: number | null): Row[] {
  return steps.flatMap((step, i): Row[] => {
    if (step.kind === "module") {
      return [{ key: `m${String(i)}`, ...step, group: null, revealedFirst: false }];
    }
    if (!opened.has(i)) {
      return [
        {
          key: `g${String(i)}`,
          name: step.title,
          state: step.state,
          detail: null,
          group: { index: i, showAll: step.showAll },
          revealedFirst: false,
        },
      ];
    }
    return step.modules.map((m, j) => ({
      key: `g${String(i)}-${String(j)}`,
      ...m,
      group: null,
      revealedFirst: j === 0 && i === last,
    }));
  });
}

function ModuleBadge({ word, live }: { word: ModuleWord; live: boolean }) {
  if (word === "Not assessable" || word === "Not run") {
    return <StatusBadge set="Module state" state={word} />;
  }
  return <StatusBadge set="Run states" state={word} live={live} />;
}

function Marker({ word }: { word: ModuleWord }) {
  return (
    <span
      aria-hidden="true"
      className={cx(
        "z-10 flex size-6 shrink-0 items-center justify-center rounded-full",
        word === "Finished" && "bg-action text-text-on-action",
        word === "Running" &&
          "bg-action shadow-[0_0_0_2px_var(--color-surface-card),0_0_0_4px_var(--color-action)]",
        word !== "Finished" &&
          word !== "Running" &&
          "bg-surface-card inset-ring-[1.5px] inset-ring-border-container",
      )}
    >
      {word === "Finished" ? (
        <Check className="size-4" />
      ) : (
        <span
          className={cx(
            "size-2 rounded-full",
            word === "Running" ? "bg-text-on-action" : "bg-text-disabled",
          )}
        />
      )}
    </span>
  );
}

function ShowAll({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <button
      type="button"
      aria-expanded="false"
      onClick={onPress}
      className="w-fit rounded-xs text-sm text-text-link underline focus-visible:outline-2 focus-visible:outline-solid focus-visible:outline-offset-2 focus-visible:outline-focus"
    >
      {label}
    </button>
  );
}

/** Vertical progress steps, one per module, each with its state as a trailing badge. */
export function ModuleSteps({ steps, live }: { steps: ModuleStep[]; live: boolean }) {
  const [opened, setOpened] = useState<ReadonlySet<number>>(new Set());
  // The group just opened: its first module's name takes focus, so the button that went does not
  // leave keyboard focus on nothing.
  const [lastOpened, setLastOpened] = useState<number | null>(null);
  const target = useRef<HTMLSpanElement | null>(null);
  useEffect(() => {
    if (lastOpened !== null) target.current?.focus();
  }, [lastOpened]);
  const rows = rowsOf(steps, opened, lastOpened);
  return (
    <ol aria-label="Modules in this run">
      {rows.map((step, i) => {
        const last = i === rows.length - 1;
        const { name, detail, group } = step;
        const waiting = live && step.state === "Queued";
        return (
          <li
            key={step.key}
            aria-current={step.state === "Running" ? "step" : undefined}
            className="flex items-start gap-3"
          >
            <div className="flex flex-none flex-col items-center self-stretch">
              <Marker word={step.state} />
              <span
                aria-hidden="true"
                className={cx(
                  "my-1 min-h-3 flex-1 rounded-xs border-s-2",
                  last && "border-transparent",
                  !last && step.state === "Finished" && "border-action",
                  !last && step.state !== "Finished" && "border-border-hairline",
                )}
              />
            </div>
            <div
              className={cx(
                "flex min-w-0 flex-1 items-start justify-between gap-3 pt-0.5",
                last ? "pb-0" : "pb-6",
              )}
            >
              <div className="flex min-w-0 flex-1 flex-col">
                <span
                  ref={step.revealedFirst ? target : undefined}
                  tabIndex={step.revealedFirst ? -1 : undefined}
                  className={cx(
                    "rounded-xs text-sm font-semibold focus-visible:outline-2 focus-visible:outline-solid focus-visible:outline-offset-2 focus-visible:outline-focus",
                    step.state === "Running" ? "text-action" : "text-text-secondary",
                  )}
                >
                  {name}
                </span>
                {group === null ? null : (
                  <ShowAll
                    label={group.showAll}
                    onPress={() => {
                      setOpened(new Set(opened).add(group.index));
                      setLastOpened(group.index);
                    }}
                  />
                )}
                {detail === null ? null : (
                  <span className="text-sm text-pretty text-text-tertiary">{detail}</span>
                )}
                {waiting ? (
                  <div aria-hidden="true" className="flex max-w-80 flex-col gap-1.5 pt-1.5">
                    <div className="activity-skel queued-shimmer w-[90%]" />
                    <div className="activity-skel queued-shimmer w-[60%]" />
                  </div>
                ) : null}
              </div>
              <ModuleBadge word={step.state} live={live} />
            </div>
          </li>
        );
      })}
    </ol>
  );
}
