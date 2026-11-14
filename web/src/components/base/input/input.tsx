import type { ComponentType, HTMLAttributes, ReactNode, Ref } from "react";
import type { TextFieldProps as AriaTextFieldProps } from "react-aria-components";
import {
  Group as AriaGroup,
  Input as AriaInput,
  TextField as AriaTextField,
} from "react-aria-components";
import { HintText } from "@/components/base/input/hint-text";
import { Label } from "@/components/base/input/label";
import { StatusShape } from "@/components/status/shapes";
import { cx } from "@/utils/cx";

export interface InputProps extends AriaTextFieldProps {
  /** Label text for the input */
  label?: string;
  /** Helper text displayed below the input, or the error message when the input is invalid */
  hint?: ReactNode;
  /** Placeholder text. */
  placeholder?: string;
  /** Ref for the underlying input element. */
  ref?: Ref<HTMLInputElement>;
  /** Icon component to display on the left side of the input. */
  icon?: ComponentType<HTMLAttributes<HTMLOrSVGElement>>;
}

export const Input = ({
  placeholder,
  icon: Icon,
  label,
  hint,
  className,
  ref,
  ...props
}: InputProps) => {
  return (
    <AriaTextField
      aria-label={!label ? placeholder : undefined}
      {...props}
      data-input-wrapper
      data-input-size="md"
      className={(state) =>
        cx(
          "group flex h-max w-full flex-col items-start justify-start gap-1.5",
          typeof className === "function" ? className(state) : className,
        )
      }
    >
      {({ isRequired, isInvalid }) => (
        <>
          {label && (
            <Label isRequired={isRequired} isInvalid={isInvalid}>
              {label}
            </Label>
          )}

          <AriaGroup
            isDisabled={props.isDisabled}
            isInvalid={isInvalid}
            className={({ isFocusWithin, isDisabled, isInvalid }) =>
              cx(
                "group/input relative flex w-full flex-row place-content-center place-items-center rounded-lg bg-primary shadow-xs ring-1 ring-primary transition-shadow duration-100 ease-linear ring-inset",

                isFocusWithin && !isDisabled && "ring-2 ring-brand",

                // Disabled state styles
                isDisabled && "cursor-not-allowed opacity-50",
                "group-disabled:cursor-not-allowed group-disabled:opacity-50",

                // Invalid state styles
                isInvalid && "ring-error_subtle",
                "group-invalid:ring-error_subtle",

                // Invalid state with focus-within styles
                isInvalid && isFocusWithin && "ring-2 ring-error",
                isFocusWithin && "group-invalid:ring-2 group-invalid:ring-error",
              )
            }
          >
            {Icon && (
              <Icon
                className={cx("pointer-events-none absolute text-fg-quaternary", "left-3 size-5")}
              />
            )}

            <AriaInput
              ref={ref}
              placeholder={placeholder}
              className={cx(
                "m-0 w-full bg-transparent text-primary ring-0 outline-hidden placeholder:text-placeholder autofill:rounded-lg autofill:text-primary disabled:cursor-not-allowed",
                cx("px-3 py-2 text-md", Icon && "pl-10", isInvalid && "pr-9"),
              )}
            />

            {/* Invalid mark: the Error status shape, in the error mark colour */}
            {isInvalid && (
              <span className="pointer-events-none absolute right-3 flex size-4 items-center justify-center text-error-mark">
                <StatusShape shape="diamond" />
              </span>
            )}
          </AriaGroup>

          {hint && <HintText isInvalid={isInvalid}>{hint}</HintText>}
        </>
      )}
    </AriaTextField>
  );
};

Input.displayName = "Input";
