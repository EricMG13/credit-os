import { useState } from "react";
import { cx } from "@/utils/cx";

export type SectionEntry = { id: string; label: string };

/** Smooth only when the reader has not asked for less motion. */
function scrollBehavior(): ScrollBehavior {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}

/**
 * A vertical menu of in-page jumps. The app routes on the hash, so an entry is a button: it moves
 * focus to the section (a heading or a labelled section with `tabIndex={-1}`) and scrolls it into
 * view inside whichever element scrolls. The mark follows the entry last used; nothing watches
 * the scroll position. Kit need: the kit has no in-page section menu.
 */
export function SectionIndex({ entries }: { entries: SectionEntry[] }) {
  const [active, setActive] = useState<string | null>(null);
  function jump(id: string) {
    const target = document.getElementById(id);
    if (target === null) throw new Error(`the section "${id}" is not on the page`);
    setActive(id);
    target.focus({ preventScroll: true });
    target.scrollIntoView({ behavior: scrollBehavior(), block: "start" });
  }
  return (
    <nav
      aria-label="On this page"
      className="flex w-full flex-none flex-col min-[900px]:sticky min-[900px]:top-6 min-[900px]:w-58 min-[900px]:self-start"
    >
      {entries.map((entry) => (
        <button
          key={entry.id}
          type="button"
          aria-current={active === entry.id ? "true" : undefined}
          onClick={() => {
            jump(entry.id);
          }}
          className={cx(
            "flex items-center gap-2 border-l-[3px] px-4 py-3 text-left text-sm font-medium outline-focus focus-visible:outline-2 focus-visible:-outline-offset-2",
            active === entry.id
              ? "border-action bg-surface-selected text-action"
              : "border-transparent text-text-tertiary hover:text-text-primary",
          )}
        >
          {entry.label}
        </button>
      ))}
    </nav>
  );
}
