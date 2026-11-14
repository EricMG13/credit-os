import type { ReactNode, Ref } from "react";
import type { LabelProps as AriaLabelProps } from "react-aria-components";
import { Label as AriaLabel } from "react-aria-components";
import { cx } from "@/utils/cx";

interface LabelProps extends AriaLabelProps {
  /** The label text, rendered before the required asterisk and the tooltip trigger. */
  children: ReactNode;
  /** Whether the required asterisk is tinted with the error color. When left undefined, it follows the invalid state of the surrounding field instead. */
  isInvalid?: boolean;
  /** Whether the required asterisk is shown. When left undefined, it appears only if the surrounding field is marked required. */
  isRequired?: boolean;
  /** Ref to the underlying label element. */
  ref?: Ref<HTMLLabelElement>;
}

export const Label = ({ isInvalid, isRequired, className, ...props }: LabelProps) => {
  return (
    <AriaLabel
      // Used for conditionally hiding/showing the label element via CSS:
      // <Input label="Visible only on mobile" className="lg:**:data-label:hidden" />
      // or
      // <Input label="Visible only on mobile" className="lg:label:hidden" />
      data-label="true"
      {...props}
      className={cx(
        "flex cursor-default items-center gap-0.5 text-sm font-medium text-secondary",
        className,
      )}
    >
      {props.children}

      <span
        className={cx(
          "hidden text-brand-tertiary",
          isRequired && "block",
          typeof isRequired === "undefined" && "group-required:block",

          isInvalid && "text-error-primary",
          typeof isInvalid === "undefined" && "group-invalid:text-error-primary",
        )}
      >
        *
      </span>
    </AriaLabel>
  );
};

Label.displayName = "Label";
