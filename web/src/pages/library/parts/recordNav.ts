import type { RecordBlock } from "../slice";
import type { NavSection } from "./ModuleNav";

/** What a navigator entry moves to: the first block that names it. */
export type RecordSection = NavSection & { first: RecordBlock };

/**
 * The navigator entries of a module's record blocks, in page order. Blocks that carry a `nav` label
 * give one entry for each distinct label; blocks without one (the prose module's) share "Records".
 */
export function recordSections(blocks: readonly RecordBlock[]): RecordSection[] {
  const sections: RecordSection[] = [];
  for (const block of blocks) {
    const label = "nav" in block ? block.nav : null;
    if (label !== null && !sections.some((section) => section.label === label)) {
      sections.push({
        key: `records-${String(sections.length)}`,
        label,
        icon: "records",
        first: block,
      });
    }
  }
  const first = blocks[0];
  if (sections.length === 0 && first !== undefined) {
    return [{ key: "records", label: "Records", icon: "records", first }];
  }
  return sections;
}
