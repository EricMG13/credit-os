import type { FC, ReactNode } from "react";
import { isValidElement } from "react";
import type { ButtonProps as AriaButtonProps } from "react-aria-components";
import { Button as AriaButton } from "react-aria-components";
import { Tooltip } from "@/components/base/tooltip/tooltip";
import { cx } from "@/utils/cx";
import { isReactComponent } from "@/utils/is-react-component";

// The `xs` size, `tertiary` colour and button (not link) form only: the file row's delete uses it.
const tertiary = "text-fg-quaternary hover:bg-primary_hover hover:text-fg-quaternary_hover";

export interface ButtonUtilityProps extends Omit<AriaButtonProps, "children" | "className"> {
  /** The icon to display in the button */
  icon?: FC<{ className?: string }> | ReactNode;
  /** The tooltip to display when hovering over the button; it is also the accessible name. */
  tooltip: string;
  /** The class name applied to the button. */
  className?: string;
}

export const ButtonUtility = ({
  tooltip,
  className,
  isDisabled,
  icon: Icon,
  ...props
}: ButtonUtilityProps) => (
  <Tooltip title={tooltip} placement="top" isDisabled={isDisabled} offset={4}>
    <AriaButton
      aria-label={tooltip}
      {...props}
      isDisabled={isDisabled}
      type={props.type ?? "button"}
      className={cx(
        "group relative inline-flex h-max cursor-pointer items-center justify-center rounded-md p-1.5 outline-focus-ring transition duration-100 ease-linear focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
        tertiary,

        // Icon styles
        "*:data-icon:pointer-events-none *:data-icon:shrink-0 *:data-icon:text-current *:data-icon:transition-inherit-all",
        "*:data-icon:size-4",

        className,
      )}
    >
      {isReactComponent(Icon) && <Icon data-icon />}
      {isValidElement(Icon) && Icon}
    </AriaButton>
  </Tooltip>
);
