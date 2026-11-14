import { ChevronRight, Cube01 } from "@untitledui/icons";
import { Link } from "react-aria-components";
import { StatusBadge } from "@/components/status/StatusBadge";
import type { ModuleItem } from "../slice";
import { modulesHref } from "./links";

const ROW = "flex flex-wrap items-center gap-4 border-b border-border-hairline p-4 text-small";

function Row({ item }: { item: ModuleItem }) {
  return (
    <>
      <span className="mt-0.5 flex size-8 flex-none items-center justify-center self-start rounded-md border border-border-hairline bg-surface-subtle text-text-tertiary">
        <Cube01 aria-hidden="true" className="size-4" />
      </span>
      <span className="flex min-w-50 flex-1 flex-col gap-1">
        <span className="font-medium text-text-primary">{item.title}</span>
        <span className="text-text-secondary">{item.lead}</span>
      </span>
      <span className="flex items-center gap-2">
        <StatusBadge set="Module state" state={item.state} />
        {item.module === null ? (
          <ChevronRight aria-hidden="true" className="size-4 text-text-tertiary" />
        ) : null}
      </span>
    </>
  );
}

/**
 * The module items (R7), two columns from the medium width, column by column. An item with a module
 * opens that module's page; one without (a repeated state collapsed into one item) is plain.
 */
export function ModuleItems({
  items,
  issuer,
  run,
}: {
  items: readonly ModuleItem[];
  issuer: string;
  run: string;
}) {
  return (
    <ul className="md:columns-2 md:gap-x-12">
      {items.map((item) => (
        <li key={item.title} className="break-inside-avoid">
          {item.module === null ? (
            <div className={ROW}>
              <Row item={item} />
            </div>
          ) : (
            <Link
              href={modulesHref(issuer, run, item.module)}
              className={`${ROW} outline-hidden hover:bg-surface-subtle focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-inset`}
            >
              <Row item={item} />
            </Link>
          )}
        </li>
      ))}
    </ul>
  );
}
