// The feed's controls: Top or Latest (beside the view title), the kind tabs and the search field.
// All state lives in FeedPage; these draw it and report changes. Filtering is in memory.
import { useEffect, useRef, type ReactNode } from "react";
import { SearchLg } from "@untitledui/icons";
import { ButtonGroup, ButtonGroupItem } from "@/components/base/button-group/button-group";
import { Input } from "@/components/base/input/input";
import { Tab, TabList, TabPanel, Tabs } from "@/components/application/tabs/tabs";

export type FeedOrder = "top" | "latest";
export type FeedKind = "all" | "regulator" | "news" | "ratings" | "research";

const ORDERS: [FeedOrder, string][] = [
  ["top", "Top"],
  ["latest", "Latest"],
];
const KINDS: [FeedKind, string][] = [
  ["all", "All"],
  ["regulator", "Regulators"],
  ["news", "News"],
  ["ratings", "Ratings"],
  ["research", "Research"],
];

/** A key the kit's controls report must be one of ours; anything else is a wiring fault. */
function pick<T extends string>(options: [T, string][], key: unknown): T {
  const found = options.find(([id]) => id === key);
  if (found === undefined)
    throw new Error(`the control reported an unknown choice "${String(key)}"`);
  return found[0];
}

export function OrderToggle({
  order,
  onOrder,
}: {
  order: FeedOrder;
  onOrder: (order: FeedOrder) => void;
}) {
  return (
    <ButtonGroup
      size="sm"
      aria-label="Order of stories"
      selectedKeys={[order]}
      disallowEmptySelection
      onSelectionChange={(keys) => {
        const [key] = keys;
        onOrder(pick(ORDERS, key));
      }}
    >
      {ORDERS.map(([id, label]) => (
        <ButtonGroupItem key={id} id={id}>
          {label}
        </ButtonGroupItem>
      ))}
    </ButtonGroup>
  );
}

/** True when a key press should move focus to the search field. */
function wantsSearch(event: KeyboardEvent): boolean {
  if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return false;
  const target = event.target;
  const typing =
    target instanceof HTMLElement &&
    (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
  return !typing && document.querySelector("dialog[open], [role='dialog']") === null;
}

export function FeedControls({
  kind,
  onKind,
  query,
  onQuery,
  above,
  children,
}: {
  kind: FeedKind;
  onKind: (kind: FeedKind) => void;
  query: string;
  onQuery: (query: string) => void;
  /** Drawn between the controls and the panel (the new-stories pill, the alert and the status line). */
  above: ReactNode;
  /** The list for the chosen kind: it sits in the panel the selected tab names. */
  children: ReactNode;
}) {
  const field = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const listen = (event: KeyboardEvent) => {
      if (!wantsSearch(event)) return;
      event.preventDefault();
      field.current?.focus();
    };
    document.addEventListener("keydown", listen);
    return () => {
      document.removeEventListener("keydown", listen);
    };
  }, []);
  return (
    <Tabs
      selectedKey={kind}
      onSelectionChange={(key) => {
        onKind(pick(KINDS, key));
      }}
    >
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <TabList aria-label="Kind of story" size="sm" className="w-auto">
          {KINDS.map(([id, label]) => (
            <Tab key={id} id={id}>
              {label}
            </Tab>
          ))}
        </TabList>
        <div className="ml-auto w-70">
          <Input
            ref={field}
            icon={SearchLg}
            placeholder="Search stories"
            value={query}
            onChange={onQuery}
            onKeyDown={(event) => {
              if (event.key === "Escape" && query !== "") {
                event.preventDefault();
                onQuery("");
              }
            }}
          />
        </div>
      </div>
      {above}
      <TabPanel key={kind} id={kind}>
        {children}
      </TabPanel>
    </Tabs>
  );
}
