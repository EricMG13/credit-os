import { X as CloseIcon } from "@untitledui/icons";
import { Button as AriaButton, type ButtonProps as AriaButtonProps } from "react-aria-components";
import { cx } from "@/utils/cx";

// The `sm` size on the `light` theme only: the slide-out header uses it.
const root = "size-9";
const icon = "size-5";
const light =
  "text-fg-quaternary hover:bg-primary_hover hover:text-fg-quaternary_hover focus-visible:outline-2 focus-visible:outline-offset-2 outline-focus-ring";

interface CloseButtonProps extends AriaButtonProps {
  /** The accessible name of the button, applied as `aria-label`. Defaults to "Close". */
  label?: string;
  /**
   * The React Aria slot the button fills. Defaults to `"close"` so it
   * automatically closes a parent `Dialog`/`Modal` without an explicit handler.
   * Pass `null` to opt out (e.g. when used as a `SearchField` clear button it
   * is picked up regardless of slot).
   * @default "close"
   */
  slot?: string | null;
}

export const CloseButton = ({
  label,
  className,
  slot = "close",
  ...otherProps
}: CloseButtonProps) => {
  return (
    <AriaButton
      {...otherProps}
      slot={slot}
      aria-label={label || "Close"}
      className={(state) =>
        cx(
          "flex cursor-pointer items-center justify-center rounded-lg p-2 transition duration-100 ease-linear focus:outline-hidden",
          root,
          light,
          typeof className === "function" ? className(state) : className,
        )
      }
    >
      <CloseIcon aria-hidden="true" className={cx("shrink-0 transition-inherit-all", icon)} />
    </AriaButton>
  );
};
