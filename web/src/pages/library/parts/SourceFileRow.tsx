import { forwardRef } from "react";
import { StatusBadge } from "@/components/status/StatusBadge";
import type { SourceFile } from "../slice";
import { Readers } from "./Readers";
import { Snippet } from "./Snippet";
import { FOCUS } from "./Section";

/**
 * One source file (R14, read-only): its type, name, size, how much was read with the reason beside
 * it, the modules that read it and its hash to copy. The name and the hash wrap; nothing is cut.
 */
export const SourceFileRow = forwardRef<HTMLLIElement, { file: SourceFile }>(function Row(
  { file },
  ref,
) {
  return (
    <li
      ref={ref}
      tabIndex={-1}
      className={`flex flex-wrap items-start gap-3 rounded-xl border border-border-subtle bg-surface-card p-4 ${FOCUS}`}
    >
      <span className="flex size-10 flex-none items-center justify-center rounded-lg border border-border-hairline bg-surface-subtle text-xs font-semibold text-text-tertiary">
        {file.kind}
      </span>
      <div className="min-w-50 flex-1">
        <p className="font-mono text-sm font-medium break-words text-text-secondary">{file.name}</p>
        <div className="mt-0.5 flex flex-wrap items-center gap-2 text-sm text-text-tertiary">
          <span>{file.size}</span>
          <span aria-hidden="true" className="h-3 w-px bg-border-control" />
          <StatusBadge set="File state" state={file.state} />
        </div>
        {file.why === null ? null : (
          <p className="mt-1.5 text-small text-text-secondary">{file.why}</p>
        )}
      </div>
      <div className="flex w-50 flex-col items-start gap-1.5">
        <span className="text-xs text-text-tertiary">{file.readersLabel}</span>
        <Readers readers={file.readers} />
      </div>
      <div className="w-85 max-w-full">
        <Snippet
          kind="SHA-256"
          value={file.hash}
          copyLabel={`Copy hash of ${file.name}`}
          what={`The hash of ${file.name}`}
        />
      </div>
    </li>
  );
});
