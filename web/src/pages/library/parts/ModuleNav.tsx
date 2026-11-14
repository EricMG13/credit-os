import { useId } from "react";
import {
  AlertTriangle,
  Flag01,
  InfoCircle,
  LayersThree01,
  List,
  RefreshCw01,
} from "@untitledui/icons";
import { Button, Link } from "react-aria-components";
import { STATUS_SETS } from "@/components/status/sets";
import { StatusShape } from "@/components/status/shapes";
import { cx } from "@/utils/cx";
import type { ModuleState } from "../slice";
import { modulesHref } from "./links";

/** The shape's colour, as the mock's `m-ok`, `m-gap` and `m-neu` set it. */
const MARK: Record<ModuleState, string> = {
  Delivered: "text-success-mark",
  "Delivered with gaps": "text-gap-text",
  "Not assessable": "text-text-tertiary",
  "Not run": "text-text-tertiary",
};

/** The look of one entry: the vertical menu's row, with the current one marked on its left edge. */
const ENTRY =
  "flex w-full cursor-pointer items-center gap-2 border-l-[3px] border-transparent px-4 text-left text-small font-medium text-text-tertiary outline-hidden hover:bg-surface-subtle hover:text-text-secondary focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-inset";
const CURRENT = "border-action bg-surface-selected text-action hover:bg-surface-selected";

/** The icon of each section a delivered module can have, in the mock's 20px slot. */
const ICON = {
  "bottom-line": Flag01,
  findings: List,
  contrary: AlertTriangle,
  "change-view": RefreshCw01,
  records: LayersThree01,
  limitations: InfoCircle,
} as const;

/** One entry: `key` addresses its target on the page, `icon` names one of the section icons. */
export type NavSection = { key: string; label: string; icon: keyof typeof ICON };
export type NavModule = { id: string; name: string; state: ModuleState };

/**
 * The module page's navigator (N3): one vertical menu in two groups. The first moves to a section
 * of this page without changing the address; the second links every module of the run, each with
 * its state shape and word. Sticky from the wide layout, where it scrolls by itself when long.
 */
export function ModuleNav({
  issuer,
  run,
  sections,
  active,
  onSection,
  modules,
  current,
}: {
  issuer: string;
  run: string;
  sections: readonly NavSection[];
  active: string | null;
  onSection: (key: string) => void;
  modules: readonly NavModule[];
  current: string;
}) {
  const sectionsLabel = useId();
  const modulesLabel = useId();
  const heading = "px-4 pt-3 pb-1 pl-4.75 text-xs font-medium text-text-tertiary";
  return (
    <nav
      aria-label="Modules and sections"
      className="flex flex-col min-[1001px]:sticky min-[1001px]:top-6 min-[1001px]:max-h-[calc(100vh-3rem)] min-[1001px]:overflow-y-auto"
    >
      {sections.length === 0 ? null : (
        <>
          <span id={sectionsLabel} className={heading}>
            On this page
          </span>
          <ul aria-labelledby={sectionsLabel}>
            {sections.map((section) => {
              const Icon = ICON[section.icon];
              return (
                <li key={section.key}>
                  <Button
                    aria-current={section.key === active ? "location" : undefined}
                    onPress={() => {
                      onSection(section.key);
                    }}
                    className={cx(ENTRY, "py-3", section.key === active && CURRENT)}
                  >
                    <Icon aria-hidden="true" className="size-5 flex-none opacity-75" />
                    {section.label}
                  </Button>
                </li>
              );
            })}
          </ul>
        </>
      )}
      <span id={modulesLabel} className={cx(heading, sections.length > 0 && "mt-4")}>
        Modules in this run
      </span>
      <ul aria-labelledby={modulesLabel}>
        {modules.map((module) => (
          <li key={module.id}>
            <Link
              href={modulesHref(issuer, run, module.id)}
              aria-label={`${module.name}, ${module.state}`}
              aria-current={module.id === current ? "page" : undefined}
              className={cx(ENTRY, "py-2", module.id === current && CURRENT)}
            >
              <span className={cx("mx-1 flex", MARK[module.state])}>
                <StatusShape shape={STATUS_SETS["Module state"][module.state].shape} />
              </span>
              <span>{module.name}</span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
