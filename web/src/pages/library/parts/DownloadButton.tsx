import { useId } from "react";
import { Button } from "@/components/base/buttons/button";
import type { Download } from "../slice";

/**
 * A download as delivered. With an address it is a link; without one the button is disabled (not
 * focusable) and the delivered reason sits beside it. Nothing is generated in the browser.
 */
export function DownloadButton({ download }: { download: Download }) {
  const reason = useId();
  if (download.href === null) {
    return (
      <div className="flex flex-wrap items-center gap-3">
        <Button color="secondary" isDisabled aria-describedby={reason}>
          {download.label}
        </Button>
        <span id={reason} className="max-w-prose text-small text-text-secondary">
          {download.reason}
        </span>
      </div>
    );
  }
  return (
    <Button color="secondary" href={download.href} download>
      {download.label}
    </Button>
  );
}
