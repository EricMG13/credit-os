import type { FC } from "react";
import { Pressable } from "react-aria-components";
import { Tooltip } from "@/components/base/tooltip/tooltip";
import { cx } from "@/utils/cx";

interface NavButtonProps {
  /** URL to navigate to when the button is clicked. */
  href: string;
  /** Label text for the button. */
  label: string;
  /** Icon component to display. */
  icon: FC<{ className?: string }>;
  /** Whether the button is currently active. */
  current?: boolean;
}

export const NavButton = ({ current, label, href, icon: Icon }: NavButtonProps) => {
  return (
    <Tooltip title={label} placement="right">
      <Pressable>
        <a
          href={href}
          aria-label={label}
          aria-current={current ? "page" : undefined}
          className={cx(
            "group/item relative flex w-full cursor-pointer items-center justify-center gap-1 rounded-md bg-primary outline-focus-ring transition duration-100 ease-linear select-none hover:bg-primary_hover focus-visible:z-10 focus-visible:outline-2 focus-visible:outline-offset-2",
            current && "bg-secondary hover:bg-secondary",
            "size-9",
          )}
        >
          <Icon
            aria-hidden="true"
            className={cx(
              "size-5 shrink-0 text-fg-quaternary transition-inherit-all group-hover/item:text-fg-quaternary_hover",
              current && "text-brand-secondary group-hover/item:text-brand-secondary",
            )}
          />
        </a>
      </Pressable>
    </Tooltip>
  );
};
