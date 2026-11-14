import { Button } from "@/components/base/buttons/button";
import type { Published } from "../slice/types";
import { Collapsible } from "./Collapsible";

/**
 * The published model as a file the reader can keep: a Markdown file to download, or the original
 * HTML to download or open from a folded panel. The page's content security policy allows no
 * frame, so the HTML opens as a page of its own and is never embedded.
 */
export function PublishedModel({ published }: { published: Published | null }) {
  if (published === null) return null;
  if (published.kind === "markdown") {
    return (
      <Button href={published.href} download size="sm" color="link-color">
        Download published model (Markdown)
      </Button>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <Button href={published.href} download size="sm" color="link-color">
        Download original HTML
      </Button>
      <Collapsible summary="Published model (original HTML)" open={false}>
        <Button href={published.href} size="sm" color="link-color">
          Open the original HTML
        </Button>
      </Collapsible>
    </div>
  );
}
