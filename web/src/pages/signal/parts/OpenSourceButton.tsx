// The "Open source" link-button a story shows when it has a web link: opens the source in a new tab.
import { LinkExternal01 } from "@untitledui/icons";
import { Button } from "@/components/base/buttons/button";

export function OpenSourceButton({
  url,
  headline,
  className,
}: {
  url: string;
  headline: string;
  className: string;
}) {
  return (
    <Button
      size="sm"
      color="link-color"
      iconTrailing={LinkExternal01}
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`Open source: ${headline} (opens in a new tab)`}
      className={className}
    >
      Open source
    </Button>
  );
}
