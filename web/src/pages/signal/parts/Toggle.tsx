// After sources/uui/toggle.tsx, on React Aria's SwitchField and SwitchButton (react-aria-components is
// the kit's own dependency; its plain Switch is deprecated in the pinned version). The mock draws it
// as `.tg`: a 44 by 24 track, the action colour when on, a white knob. Every settings section imports
// the toggle from here only, so the kit's own can replace it in one place. No transition: nothing on
// a Signal screen animates.
import type { ReactNode } from "react";
import type { SwitchFieldProps } from "react-aria-components";
import { SwitchButton, SwitchField, Text } from "react-aria-components";
import { cx } from "@/utils/cx";

type ToggleProps = Omit<SwitchFieldProps, "children" | "className"> & {
  /** Text beside the switch; it is the switch's accessible name. Without it pass `aria-label`. */
  label?: string;
  /** Supporting text under the label, read as the switch's description. */
  hint?: ReactNode;
};

export function Toggle({ label, hint, ...field }: ToggleProps) {
  return (
    <SwitchField {...field} className="flex w-max max-w-full flex-col gap-0.5">
      <SwitchButton
        className={(state) =>
          cx("flex items-start gap-3", state.isDisabled ? "cursor-not-allowed" : "cursor-pointer")
        }
      >
        {({ isSelected, isFocusVisible, isDisabled }) => (
          <>
            <span
              className={cx(
                "block h-6 w-11 shrink-0 rounded-full p-0.5 outline-focus-ring",
                isSelected
                  ? "bg-action"
                  : "bg-surface-subtle ring-1 ring-border-control ring-inset",
                isFocusVisible && "outline-2 outline-offset-2",
                isDisabled && "opacity-50",
              )}
            >
              <span
                className={cx(
                  "block size-5 rounded-full bg-surface-card shadow-sm",
                  isSelected ? "translate-x-5" : "ring-1 ring-border-control",
                )}
              />
            </span>
            {label === undefined ? null : (
              <span className="text-md font-medium text-text-primary select-none">{label}</span>
            )}
          </>
        )}
      </SwitchButton>
      {hint === undefined || hint === null ? null : (
        <Text slot="description" className="ml-14 text-md text-text-tertiary">
          {hint}
        </Text>
      )}
    </SwitchField>
  );
}
