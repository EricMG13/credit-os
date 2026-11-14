import { ChevronRight } from "@untitledui/icons";
import { Missing } from "@/components/gap/Missing";
import type { TreeNode } from "../slice";

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

/** How a figure was derived, result first: the one tree the trace drawer and the Trace tab both draw. */
export function DerivationTree({ node, label }: { node: TreeNode; label?: string }) {
  return (
    <ul aria-label={label}>
      <Branch node={node} />
    </ul>
  );
}
