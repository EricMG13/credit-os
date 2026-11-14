// After sources/uui/avatar.tsx (the group of overlapping avatars) and avatar-count.tsx (the last
// tile carries a "+N" count). The monograms and the "+N" arrive as the strings to show.
import { Avatar } from "./Avatar";

export function AvatarGroup({ monograms, more }: { monograms: string[]; more: string | null }) {
  const shown = more === null ? monograms : [...monograms, more];
  return (
    <span className="inline-flex" aria-hidden="true">
      {shown.map((text, index) => (
        <span
          key={`${String(index)}-${text}`}
          className={
            index === 0
              ? "rounded-full ring-[1.5px] ring-surface-card"
              : "-ml-1 rounded-full ring-[1.5px] ring-surface-card"
          }
        >
          <Avatar size="xs" initials={text} />
        </span>
      ))}
    </span>
  );
}
