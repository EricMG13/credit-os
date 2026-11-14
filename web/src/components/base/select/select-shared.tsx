import type { FC, ReactNode } from "react";

export type SelectItemType = {
  /** Unique identifier for the item. */
  id: string | number;
  /** The primary display text. */
  label?: string;
  /** Whether the item is disabled. */
  isDisabled?: boolean;
  /** Secondary text displayed alongside the label. */
  supportingText?: string;
  /** Leading icon component or element. */
  icon?: FC | ReactNode;
};

export interface CommonProps {
  /** Helper text displayed below the input. */
  hint?: string;
  /** Field label displayed above the input. */
  label?: string;
  /** Placeholder text when no value is selected. */
  placeholder?: string;
  /** Whether to hide the required indicator from the label. */
  hideRequiredIndicator?: boolean;
}

export const size = {
  root: "py-2 px-3 gap-2 *:data-icon:size-5",
  withIcon: "",
  text: "text-md",
  textContainer: "gap-x-1.5",
  shortcut: "pr-2.5",
};
