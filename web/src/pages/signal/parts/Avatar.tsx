// After sources/uui/avatar.tsx and avatar-label-group.tsx, reduced to what Signal draws: a round
// avatar with initials or a person icon, and the avatar with a title and a subtitle beside it.
import type { ReactNode } from "react";
import { User01 } from "@untitledui/icons";
import { cx } from "@/utils/cx";

const SIZES = {
  xs: { box: "size-6", initials: "text-xs", icon: "size-3" },
  sm: { box: "size-8", initials: "text-sm", icon: "size-4" },
  md: { box: "size-10", initials: "text-md", icon: "size-5" },
} as const;

type AvatarProps = {
  size: keyof typeof SIZES;
  /** Without initials the avatar draws a person icon. */
  initials: string | null;
  /** The tinted form the mock gives the viewer's own avatar. */
  own?: boolean;
};

/** Decoration: the name beside it carries the meaning, so it is hidden from the accessibility tree. */
export function Avatar({ size, initials, own = false }: AvatarProps) {
  return (
    <span
      aria-hidden="true"
      className={cx(
        "inline-flex shrink-0 items-center justify-center rounded-full font-semibold ring-[0.5px] ring-border-subtle ring-inset",
        SIZES[size].box,
        own ? "bg-surface-selected text-text-link" : "bg-surface-subtle text-text-tertiary",
      )}
    >
      {initials === null ? (
        <User01 className={SIZES[size].icon} />
      ) : (
        <span className={SIZES[size].initials}>{initials}</span>
      )}
    </span>
  );
}

type AvatarLabelGroupProps = AvatarProps & { title: ReactNode; subtitle: ReactNode };

export function AvatarLabelGroup({ title, subtitle, ...avatar }: AvatarLabelGroupProps) {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <Avatar {...avatar} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-text-primary">{title}</p>
        <p className="text-xs text-text-tertiary">{subtitle}</p>
      </div>
    </div>
  );
}
