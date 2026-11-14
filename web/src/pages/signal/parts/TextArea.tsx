// After sources/uui/textarea.tsx (I8): a labelled text area with a hint that becomes the error
// message when the field is invalid. The source's resize-handle image carries raw colours, so the
// browser's own handle stays. Without a visible `label` the field needs an `aria-label`.
import type { ReactNode, Ref } from "react";
import type { TextFieldProps as AriaTextFieldProps } from "react-aria-components";
import { TextArea as AriaTextArea, TextField as AriaTextField } from "react-aria-components";
import { HintText } from "@/components/base/input/hint-text";
import { Label } from "@/components/base/input/label";
import { cx } from "@/utils/cx";

type TextAreaProps = AriaTextFieldProps & {
  /** Label text; leave it out and give `aria-label` when the surrounding design names the field. */
  label?: string;
  /** Helper text, or the error message while the field is invalid. */
  hint?: ReactNode;
  placeholder?: string;
  rows?: number;
  /** Ref for the textarea element itself (to move focus into it). */
  textAreaRef?: Ref<HTMLTextAreaElement>;
};

export function TextArea({
  label,
  hint,
  placeholder,
  rows,
  textAreaRef,
  className,
  ...props
}: TextAreaProps) {
  return (
    <AriaTextField
      {...props}
      className={(state) =>
        cx(
          "group flex h-max w-full flex-col items-start justify-start gap-1.5",
          typeof className === "function" ? className(state) : className,
        )
      }
    >
      {({ isInvalid, isRequired }) => (
        <>
          {label ? (
            <Label isRequired={isRequired} isInvalid={isInvalid}>
              {label}
            </Label>
          ) : null}
          <AriaTextArea
            ref={textAreaRef}
            placeholder={placeholder}
            rows={rows}
            className={(state) =>
              cx(
                "w-full scroll-py-3 rounded-lg bg-primary px-3.5 py-3 text-md text-primary shadow-xs ring-1 ring-primary transition duration-100 ease-linear ring-inset placeholder:text-placeholder focus:outline-hidden",
                state.isFocused && !state.isDisabled && "ring-2 ring-brand",
                state.isDisabled && "cursor-not-allowed opacity-50",
                state.isInvalid && "ring-error_subtle",
                state.isInvalid && state.isFocused && "ring-2 ring-error",
              )
            }
          />
          {hint ? <HintText isInvalid={isInvalid}>{hint}</HintText> : null}
        </>
      )}
    </AriaTextField>
  );
}
