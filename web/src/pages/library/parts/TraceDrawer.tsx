import { ChevronRight } from "@untitledui/icons";
import { Button } from "@/components/base/buttons/button";
import { SlideoutMenu } from "@/components/application/slideout-menus/slideout-menu";
import { Missing } from "@/components/gap/Missing";
import type { Trace, TreeNode } from "../slice";
import { ButtonLink } from "./ButtonLink";

function Row({ node }: { node: TreeNode }) {
  return (
    <span className="flex min-w-0 flex-col text-small font-semibold text-text-primary">
      <span>
        <span className="font-medium text-text-tertiary">{node.label}</span>{" "}
        {node.value === null ? <Missing /> : node.value}
      </span>
      {node.note === null ? null : (
        <span className="font-mono text-mono font-normal break-words text-text-tertiary">
          {node.note}
        </span>
      )}
    </span>
  );
}

const ROW = "flex items-start gap-2 rounded-ds-xs px-2 py-1.5";

/** A branch is a native `details`: Enter or Space on its summary opens and closes it. */
function Branch({ node }: { node: TreeNode }) {
  if (node.children.length === 0) {
    return (
      <li className={ROW}>
        <span className="w-4 flex-none" />
        <Row node={node} />
      </li>
    );
  }
  return (
    <li>
      <details open className="group/branch">
        <summary
          className={`${ROW} cursor-pointer list-none outline-hidden hover:bg-surface-subtle focus-visible:ring-2 focus-visible:ring-brand [&::-webkit-details-marker]:hidden`}
        >
          <ChevronRight
            aria-hidden="true"
            className="mt-0.5 size-4 flex-none text-text-tertiary transition-transform duration-150 group-open/branch:rotate-90 motion-reduce:transition-none"
          />
          <Row node={node} />
        </summary>
        <ul className="ml-4 border-l border-border-hairline pl-2">
          {node.children.map((child, index) => (
            <Branch key={`${String(index)}-${child.label}`} node={child} />
          ))}
        </ul>
      </details>
    </li>
  );
}

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
          <ul>
            <Branch node={trace.derivation} />
          </ul>
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
        <ButtonLink href={evidenceHref} onPress={onClose}>
          Open in Evidence
        </ButtonLink>
      </SlideoutMenu.Footer>
    </SlideoutMenu>
  );
}
