import { isValidElement } from "react";
import { Check } from "@untitledui/icons";
import type { ListBoxItemProps as AriaListBoxItemProps } from "react-aria-components";
import { ListBoxItem as AriaListBoxItem, Text as AriaText } from "react-aria-components";
import { cx } from "@/utils/cx";
import { isReactComponent } from "@/utils/is-react-component";
import type { SelectItemType } from "./select-shared";

const size = {
  root: "p-2 pr-2.5 gap-2 *:data-icon:size-5",
  text: "text-md",
  textContainer: "gap-x-2",
  check: "size-5",
};

interface SelectItemProps
  extends Omit<AriaListBoxItemProps<SelectItemType>, "id">, SelectItemType {}

export const SelectItem = ({
  label,
  id,
  value,
  supportingText,
  isDisabled,
  icon: Icon,
  className,
  children,
  ...props
}: SelectItemProps) => {
  const labelOrChildren = label || (typeof children === "string" ? children : "");
  const textValue = supportingText ? labelOrChildren + " " + supportingText : labelOrChildren;

  return (
    <AriaListBoxItem
      id={id}
      value={
        value ?? {
          id,
          label: labelOrChildren,
          supportingText,
          isDisabled,
          icon: Icon,
        }
      }
      textValue={textValue}
      isDisabled={isDisabled}
      {...props}
      className={(state) =>
        cx(
          "w-full px-1.5 py-px outline-hidden",
          typeof className === "function" ? className(state) : className,
        )
      }
    >
      {(state) => (
        <div
          className={cx(
            "flex cursor-pointer items-center rounded-md outline-hidden select-none",
            (state.isFocused || state.isHovered || state.isSelected) && "bg-primary_hover",
            state.isDisabled && "cursor-not-allowed opacity-50",
            state.isFocusVisible && "ring-2 ring-focus-ring ring-inset",

            // Icon styles
            "*:data-icon:shrink-0 *:data-icon:text-fg-quaternary",

            size.root,
          )}
        >
          {isReactComponent(Icon) ? (
            <Icon data-icon aria-hidden="true" />
          ) : isValidElement(Icon) ? (
            Icon
          ) : null}

          <div className={cx("flex w-full min-w-0 flex-1 flex-wrap", size.textContainer)}>
            <AriaText
              slot="label"
              className={cx("truncate font-medium whitespace-nowrap text-primary", size.text)}
            >
              {label || (typeof children === "function" ? children(state) : children)}
            </AriaText>

            {supportingText && (
              <AriaText
                slot="description"
                className={cx("whitespace-nowrap text-tertiary", size.text)}
              >
                {supportingText}
              </AriaText>
            )}
          </div>

          {state.isSelected && (
            <Check aria-hidden="true" className={cx("ml-auto text-fg-brand-primary", size.check)} />
          )}
        </div>
      )}
    </AriaListBoxItem>
  );
};
