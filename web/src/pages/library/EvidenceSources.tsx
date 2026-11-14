import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/base/buttons/button";
import type { Evidence, Reader } from "./slice";
import { NothingForModule } from "./parts/ModuleFilter";
import { SourceFileRow } from "./parts/SourceFileRow";
import { QuietSection } from "./parts/Section";

/**
 * The Sources tab: one row for each file the run read. The first `visible` rows show, the rest
 * wait behind the delivered label. With a module chosen, every file that module read shows (ids
 * only are compared) and nothing is held back; a module that read none draws an empty state.
 */
export function EvidenceSources({
  sources,
  module,
  onClear,
}: {
  sources: Evidence["sources"];
  /** The module the filter names, or `null` for all. */
  module: Reader | null;
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
            file.readers.shown.some((reader) => reader.id === module.id) ||
            file.readers.more?.ids.includes(module.id) === true,
        );
  const files = filtered ?? (expanded ? sources.files : sources.files.slice(0, sources.visible));
  if (module !== null && filtered?.length === 0) {
    return (
      <NothingForModule
        title={`No file was read by ${module.name}`}
        clearLabel="Show all files"
        onClear={onClear}
      />
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
