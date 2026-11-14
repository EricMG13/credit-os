import type { ReactNode } from "react";
import { Dot } from "@/components/foundations/dot-icon";
import { cx } from "@/utils/cx";
import type { BadgeColors, Sizes } from "./badge-types";

const colors: Record<BadgeColors, { root: string; addon: string }> = {
  gray: {
    root: "bg-utility-neutral-50 text-utility-neutral-700 ring-utility-neutral-200",
    addon: "text-utility-neutral-500",
  },
  brand: {
    root: "bg-utility-brand-50 text-utility-brand-700 ring-utility-brand-200",
    addon: "text-utility-brand-500",
  },
  error: {
    root: "bg-utility-red-50 text-utility-red-700 ring-utility-red-200",
    addon: "text-utility-red-500",
  },
  warning: {
    root: "bg-utility-yellow-50 text-utility-yellow-700 ring-utility-yellow-200",
    addon: "text-utility-yellow-500",
  },
  success: {
    root: "bg-utility-green-50 text-utility-green-700 ring-utility-green-200",
    addon: "text-utility-green-500",
  },
  sky: {
    root: "bg-utility-sky-50 text-utility-sky-700 ring-utility-sky-200",
    addon: "text-utility-sky-500",
  },
  gap: {
    root: "bg-white text-gap-text border border-dashed border-border-gap ring-0",
    addon: "text-gap-text",
  },
};

const common = "size-max flex items-center whitespace-nowrap rounded-full ring-1 ring-inset";

interface BadgeProps {
  /** Controls the padding and font size of the badge. */
  size?: Sizes;
  /** The color palette used for the badge background, text, and ring. */
  color?: BadgeColors;
  /** A leading mark, such as a status shape, drawn before the label. */
  icon?: ReactNode;
  /** The content of the badge, usually a short text label. */
  children: ReactNode;
  /** Additional CSS classes merged onto the badge element. */
  className?: string;
}

export const Badge = ({ size = "md", color = "gray", icon, children, className }: BadgeProps) => {
  const sizes = {
    sm: "py-0.5 px-2 text-xs font-medium",
    md: "py-0.5 px-2.5 text-sm font-medium",
    lg: "py-1 px-3 text-sm font-medium",
  };

  return (
    <span className={cx(common, sizes[size], colors[color].root, className)}>
      {icon}
      {children}
    </span>
  );
};

export const BadgeWithDot = ({
  size = "md",
  color = "gray",
  children,
  className,
}: Omit<BadgeProps, "icon">) => {
  const sizes = {
    sm: "gap-1 py-0.5 pl-1.5 pr-2 text-xs font-medium",
    md: "gap-1.5 py-0.5 pl-2 pr-2.5 text-sm font-medium",
    lg: "gap-1.5 py-1 pl-2.5 pr-3 text-sm font-medium",
  };

  return (
    <span className={cx(common, sizes[size], colors[color].root, className)}>
      <Dot className={colors[color].addon} />
      {children}
    </span>
  );
};
