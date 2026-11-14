import { useState } from "react";
import {
  FileUpload,
  type FileListItemProps,
} from "@/components/application/file-upload/file-upload-base";

type Row = Pick<FileListItemProps, "name" | "size" | "state" | "progress">;

const ROWS: Row[] = [
  {
    name: "Annual report.pdf",
    size: "4 MB",
    state: "Uploading",
    progress: { value: 40, label: "40%" },
  },
  {
    name: "Credit agreement.pdf",
    size: "1 MB",
    state: "Read in full",
    progress: { value: 100, label: "100%" },
  },
  { name: "Covenant schedule.xlsx", size: "320 KB", state: "Read in part" },
  { name: "Scanned notes.pdf", size: "9 MB", state: "Unreadable" },
];

/** The kit's file upload section: the drop zone and one row per file state. Delete removes a row; retry puts it back to Uploading with no progress known. */
export function KitFileUpload() {
  const [chosen, setChosen] = useState<string | null>(null);
  const [rows, setRows] = useState<Row[]>(ROWS);
  return (
    <section aria-labelledby="kit-file-upload" className="mt-8 flex flex-col gap-4">
      <h2 id="kit-file-upload" className="font-display text-h2 text-text-primary">
        File upload
      </h2>
      <FileUpload.Root className="max-w-xl">
        <FileUpload.DropZone
          hint="PDF, XLSX or DOCX files"
          onDropFiles={(files) => {
            setChosen(files.map((f) => f.name).join(", "));
          }}
        />
        <p aria-live="polite" className="text-small text-text-secondary">
          {chosen !== null && `Chosen: ${chosen}`}
        </p>
        <FileUpload.List>
          {rows.map((r) => (
            <FileUpload.ListItemProgressBar
              key={r.name}
              {...r}
              onDelete={() => {
                setRows((all) => all.filter((x) => x.name !== r.name));
              }}
              onRetry={() => {
                setRows((all) =>
                  all.map((x) =>
                    x.name === r.name ? { name: x.name, size: x.size, state: "Uploading" } : x,
                  ),
                );
              }}
            />
          ))}
        </FileUpload.List>
      </FileUpload.Root>
    </section>
  );
}
