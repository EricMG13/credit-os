import { useEffect, useRef, useState } from "react";
import { FilterLines } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { Button } from "@/components/base/buttons/button";
import type { Evidence } from "./slice";
import { SourceFileRow } from "./parts/SourceFileRow";
import { QuietSection } from "./parts/Section";
import { SUBSECTION_HEADING } from "./parts/heading";

/**
 * The Sources tab: one row for each file the run read. The first `visible` rows show, the rest
 * wait behind the delivered label. With a module chosen, every file that module read shows (ids
 * only are compared) and nothing is held back; a module that read none draws an empty state.
 */
export function EvidenceSources({
  sources,
  module,
  moduleName,
  onClear,
}: {
  sources: Evidence["sources"];
  /** The id of the module the filter names, or `null` for all. */
  module: string | null;
  moduleName: string | null;
  onClear: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const firstRevealed = useRef<HTMLLIElement>(null);
  useEffect(() => {
    if (expanded) firstRevealed.current?.focus();
  }, [expanded]);
  const filtered =
    module === null
      ? null
      : sources.files.filter(
          (file) =>
            file.readers.shown.some((reader) => reader.id === module) ||
            file.readers.more?.ids.includes(module) === true,
        );
  const files = filtered ?? (expanded ? sources.files : sources.files.slice(0, sources.visible));
  if (filtered?.length === 0) {
    return (
      <EmptyState>
        <EmptyState.Header>
          <EmptyState.FeaturedIcon icon={FilterLines} />
        </EmptyState.Header>
        <EmptyState.Content>
          <EmptyState.Title as={SUBSECTION_HEADING}>
            No file was read by {moduleName}
          </EmptyState.Title>
          <EmptyState.Description>Choose another module, or all of them.</EmptyState.Description>
        </EmptyState.Content>
        <EmptyState.Footer>
          <Button color="secondary" onPress={onClear}>
            Show all files
          </Button>
        </EmptyState.Footer>
      </EmptyState>
    );
  }
  return (
    <QuietSection title="Source files">
      <div className="flex flex-col items-start gap-4">
        <ul className="flex w-full flex-col gap-3">
          {files.map((file, index) => (
            <SourceFileRow
              key={file.name}
              file={file}
              ref={filtered === null && index === sources.visible ? firstRevealed : undefined}
            />
          ))}
        </ul>
        {filtered !== null || expanded || sources.moreLabel === null ? null : (
          <Button
            color="secondary"
            onPress={() => {
              setExpanded(true);
            }}
          >
            {sources.moreLabel}
          </Button>
        )}
      </div>
    </QuietSection>
  );
}
