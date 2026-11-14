import type { FC, ReactNode, Ref, RefAttributes } from "react";
import { isValidElement } from "react";
import { ChevronDown } from "@untitledui/icons";
import type { SelectProps as AriaSelectProps } from "react-aria-components";
import {
  Button as AriaButton,
  ListBox as AriaListBox,
  Select as AriaSelect,
  SelectValue as AriaSelectValue,
} from "react-aria-components";
import { HintText } from "@/components/base/input/hint-text";
import { Label } from "@/components/base/input/label";
import { StatusShape } from "@/components/status/shapes";
import { cx } from "@/utils/cx";
import { isReactComponent } from "@/utils/is-react-component";
import { Popover } from "./popover";
import { SelectItem } from "./select-item";
import { type CommonProps, type SelectItemType, size } from "./select-shared";

interface SelectProps
  extends
    Omit<AriaSelectProps<SelectItemType>, "children" | "items">,
    RefAttributes<HTMLDivElement>,
    CommonProps {
  /** The options to render in the dropdown. When `children` is a function it is called once per item to render it. */
  items?: SelectItemType[];
  /** Additional classes merged onto the dropdown popover. */
  popoverClassName?: string;
  /** Leading icon shown in the trigger, used as a fallback when the selected item has no icon of its own. Accepts a component reference or a rendered element. */
  icon?: FC | ReactNode;
  /** The dropdown contents: either `Select.Item` elements, or a render function called with each entry of `items`. */
  children: ReactNode | ((item: SelectItemType) => ReactNode);
}

interface SelectValueProps {
  /** Whether the dropdown is open, which keeps the trigger in its focused ring style. */
  isOpen: boolean;
  /** Whether the trigger is focused, which draws the brand focus ring. */
  isFocused: boolean;
  /** Whether the field is invalid, which draws the error ring and the Error shape. */
  isInvalid: boolean;
  /** Whether the trigger is dimmed and rejects pointer interaction. */
  isDisabled: boolean;
  /** Text shown in the trigger while no item is selected. */
  placeholder?: string;
  /** Ref to the trigger button element. */
  ref?: Ref<HTMLButtonElement>;
  /** Leading icon shown in the trigger when the selected item has no icon of its own. */
  icon?: FC | ReactNode;
}

const SelectValue = ({
  isOpen,
  isFocused,
  isInvalid,
  isDisabled,
  placeholder,
  icon,
  ref,
}: SelectValueProps) => {
  return (
    <AriaButton
      ref={ref}
      className={cx(
        "relative flex w-full cursor-pointer items-center rounded-lg bg-primary shadow-xs ring-1 ring-primary outline-hidden transition duration-100 ease-linear ring-inset",
        isInvalid && "ring-error_subtle",
        (isFocused || isOpen) && !isInvalid && "ring-2 ring-brand",
        (isFocused || isOpen) && isInvalid && "ring-2 ring-error",
        isDisabled && "cursor-not-allowed opacity-50",
      )}
    >
      <AriaSelectValue<SelectItemType>
        className={(state) =>
          cx(
            "flex h-max w-full items-center justify-start truncate text-left align-middle",

            size.root,

            // With icon
            (state.selectedItems[0]?.icon || icon) && size.withIcon,

            // Icon styles
            "*:data-icon:shrink-0 *:data-icon:text-fg-quaternary",
          )
        }
      >
        {(state) => {
          const selectedItem = state.selectedItems[0];
          const Icon = selectedItem?.icon || icon;

          return (
            <>
              {isReactComponent(Icon) ? (
                <Icon data-icon aria-hidden="true" />
              ) : isValidElement(Icon) ? (
                Icon
              ) : null}

              {selectedItem ? (
                <section className={cx("flex w-full truncate", size.textContainer)}>
                  <p className={cx("truncate font-medium text-primary", size.text)}>
                    {selectedItem.label}
                  </p>
                  {selectedItem.supportingText && (
                    <p className={cx("text-tertiary", size.text)}>{selectedItem.supportingText}</p>
                  )}
                </section>
              ) : (
                <p className={cx("text-placeholder", size.text)}>{placeholder}</p>
              )}

              {isInvalid && (
                <span className="ml-auto flex size-4 shrink-0 items-center justify-center text-error-mark">
                  <StatusShape shape="diamond" />
                </span>
              )}
              <ChevronDown
                aria-hidden="true"
                className={cx(
                  "size-4 shrink-0 stroke-[2.25px] text-fg-quaternary",
                  !isInvalid && "ml-auto",
                )}
              />
            </>
          );
        }}
      </AriaSelectValue>
    </AriaButton>
  );
};

const Select = ({
  placeholder = "Select",
  icon,
  children,
  items,
  label,
  hint,
  hideRequiredIndicator,
  className,
  ...rest
}: SelectProps) => {
  return (
    <AriaSelect
      {...rest}
      className={(state) =>
        cx("flex flex-col gap-1.5", typeof className === "function" ? className(state) : className)
      }
    >
      {(state) => (
        <>
          {label && (
            <Label isRequired={hideRequiredIndicator ? false : state.isRequired}>{label}</Label>
          )}

          <SelectValue {...state} placeholder={placeholder} icon={icon} />

          <Popover className={rest.popoverClassName}>
            <AriaListBox items={items} className="size-full outline-hidden">
              {children}
            </AriaListBox>
          </Popover>

          {hint && <HintText isInvalid={state.isInvalid}>{hint}</HintText>}
        </>
      )}
    </AriaSelect>
  );
};

const _Select = Select as typeof Select & {
  Item: typeof SelectItem;
};
_Select.Item = SelectItem;

export { _Select as Select };
