import type { FC, ReactNode, Ref } from "react";
import { isValidElement } from "react";
import { cx } from "@/utils/cx";
import { isReactComponent } from "@/utils/is-react-component";

const iconsSizes = {
  sm: "*:data-icon:size-4 *:data-icon:stroke-[2.25px]",
  md: "*:data-icon:size-5",
  lg: "*:data-icon:size-6",
  xl: "*:data-icon:size-7",
};

// The `light` theme only: the design system names it.
const light = {
  base: "rounded-full",
  sizes: {
    sm: "size-8",
    md: "size-10",
    lg: "size-12",
    xl: "size-14",
  },
  colors: {
    brand: "bg-brand-secondary text-featured-icon-light-fg-brand",
    gray: "bg-tertiary text-featured-icon-light-fg-gray",
    error: "bg-error-secondary text-featured-icon-light-fg-error",
    warning: "bg-warning-secondary text-featured-icon-light-fg-warning",
    success: "bg-success-secondary text-featured-icon-light-fg-success",
  },
};

interface FeaturedIconProps {
  /** A ref to the wrapper element. */
  ref?: Ref<HTMLDivElement>;
  /** Extra content rendered inside the wrapper, alongside the icon. */
  children?: ReactNode;
  /** The class name applied to the wrapper. */
  className?: string;
  /** The icon to display. Accepts a component reference or a rendered element. */
  icon?: FC<{ className?: string }> | ReactNode;
  /** Controls the dimensions of the wrapper and the icon inside it. */
  size?: "sm" | "md" | "lg" | "xl";
  /** The semantic color used for the background and icon. */
  color: "brand" | "gray" | "success" | "warning" | "error";
}

export const FeaturedIcon = (props: FeaturedIconProps) => {
  const { size = "sm", color, icon: Icon, ...otherProps } = props;

  return (
    <div
      {...otherProps}
      data-featured-icon
      className={cx(
        "relative flex shrink-0 items-center justify-center",

        iconsSizes[size],
        light.base,
        light.sizes[size],
        light.colors[color],

        props.className,
      )}
    >
      {isReactComponent(Icon) && <Icon data-icon className="z-1" />}
      {isValidElement(Icon) && <div className="z-1">{Icon}</div>}

      {props.children}
    </div>
  );
};
