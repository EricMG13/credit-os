import { useId } from "react";
import { Button } from "@/components/base/buttons/button";
import type { Download } from "../slice";

/**
 * A download as delivered. With an address it is a link; without one the button is disabled (not
 * focusable) and the delivered reason sits beside it. Nothing is generated in the browser. `open`
 * draws a link that opens the file in a new tab instead of saving it, and `color` its look.
 */
export function DownloadButton({
  download,
  color = "secondary",
  open = false,
  end = false,
}: {
  download: Download;
  color?: "secondary" | "link-color";
  open?: boolean;
  /** Stacks the disabled button over its reason, both against the cell's right edge. */
  end?: boolean;
}) {
  const reason = useId();
  if (download.href === null) {
    return (
      <div
        className={end ? "flex flex-col items-end gap-1.5" : "flex flex-wrap items-center gap-3"}
      >
        <Button color={color} isDisabled aria-describedby={reason}>
          {download.label}
        </Button>
        <span
          id={reason}
          className={`max-w-prose text-small text-text-secondary${end ? " text-right" : ""}`}
        >
          {download.reason}
        </span>
      </div>
    );
  }
  return (
    <Button
      color={color}
      href={download.href}
      {...(open ? { target: "_blank", rel: "noreferrer" } : { download: true })}
    >
      {download.label}
    </Button>
  );
}
