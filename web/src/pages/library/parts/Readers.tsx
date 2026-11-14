import type { SourceFile } from "../slice";

const AVATAR =
  "-ml-1 flex size-8 flex-none items-center justify-center rounded-full bg-surface-subtle text-sm font-semibold text-text-tertiary ring-2 ring-surface-card first:ml-0";

/**
 * The modules that read a file as an avatar group of their initials, then the "+N" avatar (R15). The
 * group is one image named by the module names, so a screen reader hears them, not letters. A file
 * nobody read draws no group.
 */
export function Readers({ readers }: { readers: SourceFile["readers"] }) {
  if (readers.shown.length === 0 && readers.more === null) return null;
  const names = [...readers.shown.map((reader) => reader.name), readers.more?.label ?? null];
  return (
    <span
      role="img"
      aria-label={names.filter((name) => name !== null).join(", ")}
      className="inline-flex"
    >
      {readers.shown.map((reader) => (
        <span key={reader.id} aria-hidden="true" title={reader.name} className={AVATAR}>
          {reader.initials}
        </span>
      ))}
      {readers.more === null ? null : (
        <span aria-hidden="true" title={readers.more.label} className={AVATAR}>
          {readers.more.text}
        </span>
      )}
    </span>
  );
}
