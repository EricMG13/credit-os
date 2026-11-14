import { Button } from "@/components/base/buttons/button";
import { SlideoutMenu } from "@/components/application/slideout-menus/slideout-menu";
import type { Trace } from "../slice";
import { DerivationTree } from "./DerivationTree";

const CAPTION = "text-xs font-medium text-text-tertiary";

/** The sources of one figure: its statement and how it was derived. The one place audit material shows on a run page. */
export function TraceDrawer({
  trace,
  evidenceHref,
  isOpen,
  onClose,
}: {
  trace: Trace;
  evidenceHref: string;
  isOpen: boolean;
  onClose: () => void;
}) {
  return (
    <SlideoutMenu
      isOpen={isOpen}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      isDismissable
      aria-label={trace.title}
    >
      <SlideoutMenu.Header>
        <h2 className="pr-10 text-lg font-semibold text-text-primary">{trace.heading}</h2>
        <p className="text-small text-text-tertiary">{trace.subtitle}</p>
      </SlideoutMenu.Header>
      <SlideoutMenu.Content>
        <div className="flex flex-col gap-1.5">
          <span className={CAPTION}>The statement</span>
          <p className="text-body text-text-primary">{trace.statement}</p>
        </div>
        <div className="flex flex-col gap-1.5">
          <span className={CAPTION}>How it was derived</span>
          <DerivationTree node={trace.derivation} />
        </div>
        {trace.excerpt === null ? null : (
          <div className="flex flex-col gap-1.5">
            <span className={CAPTION}>Source excerpt</span>
            <blockquote className="rounded-ds-sm bg-surface-subtle px-4 py-3 text-small text-text-secondary">
              {trace.excerpt.quote}
            </blockquote>
            <span className="font-mono text-mono break-words text-text-tertiary">
              {trace.excerpt.source}
            </span>
          </div>
        )}
        {trace.qualification === null ? null : (
          <div className="flex flex-col gap-1.5">
            <span className={CAPTION}>Qualification</span>
            <p className="text-small text-text-secondary">{trace.qualification}</p>
          </div>
        )}
      </SlideoutMenu.Content>
      <SlideoutMenu.Footer className="flex justify-end gap-3">
        <Button color="secondary" slot="close">
          Close
        </Button>
        <Button href={evidenceHref} onPress={onClose}>
          Open in Evidence
        </Button>
      </SlideoutMenu.Footer>
    </SlideoutMenu>
  );
}
