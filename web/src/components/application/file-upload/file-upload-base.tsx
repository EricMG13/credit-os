import type { ComponentPropsWithRef } from "react";
import { useId, useRef, useState } from "react";
import { File05, Trash01, UploadCloud02 } from "@untitledui/icons";
import { Button } from "@/components/base/buttons/button";
import { ButtonUtility } from "@/components/base/buttons/button-utility";
import { ProgressBar } from "@/components/base/progress-indicators/progress-indicators";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { StatusBadge } from "@/components/status/StatusBadge";
import type { STATUS_SETS } from "@/components/status/sets";
import { cx } from "@/utils/cx";

interface FileUploadDropZoneProps {
  /** The class name of the drop zone. */
  className?: string;
  /** A hint text explaining what files can be dropped. */
  hint: string;
  /** Disables dropping or uploading files. */
  isDisabled?: boolean;
  /**
   * Specifies the types of files that the server accepts.
   * Examples: "image/*", ".pdf,image/*", "image/*,video/mpeg,application/pdf"
   */
  accept?: string;
  /** Allows multiple file uploads. */
  allowsMultiple?: boolean;
  /** Maximum file size in bytes. */
  maxSize?: number;
  /** Called with the accepted files when files are chosen or dropped. */
  onDropFiles?: (files: File[]) => void;
  /** Called with the files whose type is not accepted. */
  onDropUnacceptedFiles?: (files: File[]) => void;
  /** Called with the files that exceed the size limit. */
  onSizeLimitExceed?: (files: File[]) => void;
}

export const FileUploadDropZone = ({
  className,
  hint,
  isDisabled,
  accept,
  allowsMultiple = true,
  maxSize,
  onDropFiles,
  onDropUnacceptedFiles,
  onSizeLimitExceed,
}: FileUploadDropZoneProps) => {
  const id = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isInvalid, setIsInvalid] = useState(false);
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  const isFileTypeAccepted = (file: File): boolean => {
    if (!accept) return true;

    // Split the accept string into individual types
    const acceptedTypes = accept.split(",").map((type) => type.trim());

    return acceptedTypes.some((acceptedType) => {
      // Handle file extensions (e.g., .pdf, .doc)
      if (acceptedType.startsWith(".")) {
        const extension = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
        return extension === acceptedType.toLowerCase();
      }

      // Handle wildcards (e.g., image/*)
      if (acceptedType.endsWith("/*")) {
        const typePrefix = acceptedType.split("/")[0] ?? "";
        return file.type.startsWith(`${typePrefix}/`);
      }

      // Handle exact MIME types (e.g., application/pdf)
      return file.type === acceptedType;
    });
  };

  const handleDragIn = (event: React.DragEvent<HTMLDivElement>) => {
    if (isDisabled) return;

    event.preventDefault();
    event.stopPropagation();
    setIsDraggingOver(true);
  };

  const handleDragOut = (event: React.DragEvent<HTMLDivElement>) => {
    if (isDisabled) return;

    event.preventDefault();
    event.stopPropagation();
    setIsDraggingOver(false);
  };

  const processFiles = (files: File[]): void => {
    // Reset the invalid state when processing files.
    setIsInvalid(false);

    const acceptedFiles: File[] = [];
    const unacceptedFiles: File[] = [];
    const oversizedFiles: File[] = [];

    // If multiple files are not allowed, only process the first file
    const filesToProcess = allowsMultiple ? files : files.slice(0, 1);

    filesToProcess.forEach((file) => {
      // Check file size first
      if (maxSize !== undefined && file.size > maxSize) {
        oversizedFiles.push(file);
        return;
      }

      // Then check file type
      if (isFileTypeAccepted(file)) {
        acceptedFiles.push(file);
      } else {
        unacceptedFiles.push(file);
      }
    });

    if (oversizedFiles.length > 0) {
      setIsInvalid(true);
      onSizeLimitExceed?.(oversizedFiles);
    }

    if (acceptedFiles.length > 0) {
      onDropFiles?.(acceptedFiles);
    }

    if (unacceptedFiles.length > 0) {
      setIsInvalid(true);
      onDropUnacceptedFiles?.(unacceptedFiles);
    }

    // Clear the input value to ensure the same file can be selected again
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    if (isDisabled) return;

    handleDragOut(event);
    processFiles(Array.from(event.dataTransfer.files));
  };

  const handleInputFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    processFiles(Array.from(event.target.files ?? []));
  };

  return (
    <div
      data-dropzone
      onDragOver={handleDragIn}
      onDragEnter={handleDragIn}
      onDragLeave={handleDragOut}
      onDragEnd={handleDragOut}
      onDrop={handleDrop}
      className={cx(
        "relative flex flex-col items-center gap-3 rounded-xl bg-primary px-6 py-4 text-tertiary ring-1 ring-secondary transition duration-100 ease-linear ring-inset",
        isDraggingOver && "ring-2 ring-brand",
        isDisabled && "cursor-not-allowed bg-secondary",
        className,
      )}
    >
      <FeaturedIcon
        icon={UploadCloud02}
        color="gray"
        size="md"
        className={cx(isDisabled && "opacity-50")}
      />

      <div className="flex flex-col gap-1 text-center">
        <div className="flex justify-center gap-1 text-center">
          <input
            ref={inputRef}
            id={id}
            type="file"
            className="peer sr-only"
            tabIndex={-1}
            disabled={isDisabled}
            accept={accept}
            multiple={allowsMultiple}
            onChange={handleInputFileChange}
          />
          <label htmlFor={id} className="flex cursor-pointer">
            <Button
              color="link-color"
              size="md"
              isDisabled={isDisabled}
              onClick={() => inputRef.current?.click()}
            >
              Click to upload <span className="md:hidden">and attach files</span>
            </Button>
          </label>
          <span className="text-sm max-md:hidden">or drag and drop</span>
        </div>
        <p
          className={cx(
            "text-xs transition duration-100 ease-linear",
            isInvalid && "text-error-primary",
          )}
        >
          {hint}
        </p>
      </div>
    </div>
  );
};

export interface FileListItemProps {
  /** The name of the file. */
  name: string;
  /** The size of the file as display text, from the caller. */
  size: string;
  /** The row's state, from the File state set. */
  state: keyof (typeof STATUS_SETS)["File state"];
  /** The bar's value from 0 to 100 and the text beside it, both from the caller. Absent: no bar is drawn. */
  progress?: { value: number; label: string };
  /** The class name of the file list item. */
  className?: string;
  /** The function to call when the file is deleted. */
  onDelete?: () => void;
  /** The function to call when the file upload is retried; the retry button shows for an unreadable file only. */
  onRetry?: () => void;
}

export const FileListItemProgressBar = ({
  name,
  size,
  state,
  progress,
  onDelete,
  onRetry,
  className,
}: FileListItemProps) => {
  const failed = state === "Unreadable";

  return (
    <li
      className={cx(
        "relative flex gap-3 rounded-xl bg-primary p-4 ring-1 ring-secondary transition-shadow duration-100 ease-linear ring-inset",
        failed && "ring-2 ring-error",
        className,
      )}
    >
      <div className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-container text-fg-quaternary">
        <File05 aria-hidden="true" className="size-5" />
      </div>

      <div className="flex min-w-0 flex-1 flex-col items-start">
        <div className="flex w-full max-w-full min-w-0 flex-1">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-secondary">{name}</p>

            <div className="mt-0.5 flex items-center gap-2">
              <p className="truncate text-sm whitespace-nowrap text-tertiary">{size}</p>

              <hr className="h-3 w-px rounded-t-full rounded-b-full border-none bg-border-primary" />

              <StatusBadge set="File state" state={state} />
            </div>
          </div>

          {onDelete && (
            <ButtonUtility
              tooltip={`Delete ${name}`}
              icon={Trash01}
              className="-mt-2 -mr-2 self-start"
              onPress={onDelete}
            />
          )}
        </div>

        {!failed && progress && (
          <div className="mt-1 w-full">
            <ProgressBar value={progress.value} max={100} label={progress.label} />
          </div>
        )}

        {failed && onRetry && (
          <Button color="link-destructive" size="sm" onPress={onRetry} className="mt-1.5">
            Try again
          </Button>
        )}
      </div>
    </li>
  );
};

const FileUploadRoot = (props: ComponentPropsWithRef<"div">) => (
  <div {...props} className={cx("flex flex-col gap-4", props.className)}>
    {props.children}
  </div>
);

const FileUploadList = (props: ComponentPropsWithRef<"ul">) => (
  <ul {...props} className={cx("flex flex-col gap-3", props.className)}>
    {props.children}
  </ul>
);

export const FileUpload = {
  Root: FileUploadRoot,
  List: FileUploadList,
  DropZone: FileUploadDropZone,
  ListItemProgressBar: FileListItemProgressBar,
};
