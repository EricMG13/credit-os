import { useId } from "react";
import { Trash01 } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { FileUpload } from "@/components/application/file-upload/file-upload-base";
import { Button } from "@/components/base/buttons/button";
import { ButtonUtility } from "@/components/base/buttons/button-utility";
import { ProgressBar } from "@/components/base/progress-indicators/progress-indicators";
import { StatusBadge } from "@/components/status/StatusBadge";
import { cx } from "@/utils/cx";
import type { StartDraft } from "../slice";

const REASON =
  "Not available here: this page shows a saved example and is not connected to the run service.";

type Files = Extract<StartDraft, { step: "documents" }>["files"];

// Kit candidate: the kit's file row truncates names, shows no reason sentence and cannot
// carry the disabled Replace and Remove actions with their reason.
function FileRow({ file, reasonId }: { file: Files[number]; reasonId: string }) {
  const bad = file.state === "Unreadable";
  return (
    <li
      data-error={bad ? "" : undefined}
      className={cx(
        "flex gap-3 rounded-xl bg-primary p-4 ring-1 ring-secondary ring-inset",
        bad && "ring-2 ring-error",
      )}
    >
      <div aria-hidden="true" className="relative size-10 shrink-0">
        <div className="absolute top-0 left-[7px] h-[38px] w-[27px] rounded-tl rounded-tr-[10px] rounded-b border-[1.5px] border-container bg-primary" />
        <div className="absolute top-[18px] left-px h-4 min-w-[26px] rounded-[2px] bg-secondary px-[3px] text-center text-[9px] leading-4 font-bold tracking-[.02em] text-white">
          {file.kind}
        </div>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium wrap-anywhere text-secondary">{file.name}</p>
            <div className="mt-0.5 flex flex-wrap items-center gap-2 text-sm text-tertiary">
              <span className="tabular-nums">{file.size}</span>
              <hr className="h-3 w-px rounded-full border-none bg-border-primary" />
              <StatusBadge set="File state" state={file.state} />
            </div>
          </div>
          <ButtonUtility
            tooltip={`Remove ${file.name}`}
            icon={Trash01}
            isDisabled
            aria-describedby={reasonId}
            className="-mt-2 -mr-2 self-start"
          />
        </div>
        {file.progress === null ? null : (
          <div className="mt-1">
            <ProgressBar
              value={file.progress.value}
              max={file.progress.max}
              label={file.progress.label}
            />
          </div>
        )}
        {file.reason === null ? null : (
          <p className={cx("mt-1.5 text-sm", bad ? "text-error-primary" : "text-secondary")}>
            {file.reason}
          </p>
        )}
        {bad ? (
          <div className="mt-1.5 flex gap-3">
            <Button color="link-color" size="sm" isDisabled aria-describedby={reasonId}>
              Replace file
            </Button>
            <Button color="link-destructive" size="sm" isDisabled aria-describedby={reasonId}>
              Remove
            </Button>
          </div>
        ) : null}
      </div>
    </li>
  );
}

/** The Documents step: the drop zone (present, disabled), then the empty state or one row per file. */
export function Documents({ files }: { files: Files }) {
  const reasonId = useId();
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="font-display text-h3 text-text-primary">Documents</h2>
        <p className="text-sm text-text-secondary">
          Annual and interim reports, the credit agreement, and anything else the analysis should
          read.
        </p>
      </div>
      <FileUpload.Root>
        <div role="group" aria-label="Upload documents" aria-describedby={reasonId}>
          <FileUpload.DropZone hint="PDF, DOCX, HTML or XLSX, up to 50 MB each" isDisabled />
        </div>
        <p id={reasonId} className="text-sm text-text-secondary">
          {REASON}
        </p>
        {files.length === 0 ? (
          <EmptyState>
            <EmptyState.Header>
              <EmptyState.FeaturedIcon />
            </EmptyState.Header>
            <EmptyState.Content>
              <EmptyState.Title as="h3">No documents yet</EmptyState.Title>
              <EmptyState.Description>
                Add at least one annual report or set of accounts. The run reads only what you add
                here.
              </EmptyState.Description>
            </EmptyState.Content>
            <EmptyState.Footer>
              <Button isDisabled aria-describedby={reasonId}>
                Choose files
              </Button>
            </EmptyState.Footer>
          </EmptyState>
        ) : (
          <FileUpload.List aria-label="Documents added">
            {files.map((file, i) => (
              <FileRow key={`${String(i)}-${file.name}`} file={file} reasonId={reasonId} />
            ))}
          </FileUpload.List>
        )}
      </FileUpload.Root>
    </div>
  );
}
