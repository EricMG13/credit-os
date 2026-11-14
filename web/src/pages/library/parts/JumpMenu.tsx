import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, Calculator, Hash02, SearchLg } from "@untitledui/icons";
import {
  Autocomplete,
  Header,
  Input,
  ListBox,
  ListBoxItem,
  ListBoxSection,
  SearchField,
} from "react-aria-components";
import { Dialog, Modal, ModalOverlay } from "@/components/application/modals/modal";
import type { JumpItem } from "../slice";
import { JUMP_GROUPS } from "../slice";
import { gapItemHref, traceItemHref } from "./links";

const NAME = "Jump to an item";

/** Each group has its own mark, so a row reads as a figure, a calculation or a gap without its words. */
const ICON = { Figures: Hash02, Calculations: Calculator, Gaps: AlertTriangle } as const;
const KEY =
  "rounded-ds-xs border border-border-hairline bg-surface-card px-1.5 text-xs font-medium text-text-tertiary";

/** The shortcut as the reader's system names it: ⌘K on an Apple system, Ctrl K elsewhere. */
function shortcutLabel(): string {
  return /Mac|iPhone|iPad/.test(navigator.userAgent) ? "⌘K" : "Ctrl K";
}

/** Whether an event came from a place a reader types text, where K with a modifier is theirs. */
function isTyping(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || target.closest("input, textarea, select") !== null)
  );
}

/**
 * The "Jump to an item" field of an Evidence page and the menu it opens (the mock's command menu):
 * the items of the run in their groups, filtered by what is typed against each label, opened with
 * the arrow keys and Enter or a click, closed with Escape. The shortcut (Ctrl+K or ⌘K) is held only
 * while this is mounted, which is while an Evidence page is shown, and never taken from a text field.
 */
export function JumpMenu({
  items,
  issuer,
  run,
  onSameAddress,
}: {
  items: readonly JumpItem[];
  issuer: string;
  run: string;
  /** Called when the pick is the address already shown: the hash will not change, so the page restarts. */
  onSameAddress?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const field = useRef<HTMLButtonElement>(null);
  /** The search field takes focus as the menu opens. */
  const focusSearch = useCallback((input: HTMLInputElement | null) => {
    input?.focus();
  }, []);
  /** Opens the menu with the field focused first, so that closing it restores focus to the field. */
  const show = () => {
    field.current?.focus();
    setOpen(true);
  };
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() !== "k" || event.altKey || !(event.ctrlKey || event.metaKey))
        return;
      if (isTyping(event.target)) return;
      event.preventDefault();
      show();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
    };
  }, []);
  const go = (key: string | number) => {
    const item = items[Number(key)];
    if (item === undefined) throw new RangeError(`no jump item ${String(key)}`);
    setOpen(false);
    const href = (item.target.tab === "trace" ? traceItemHref : gapItemHref)(
      issuer,
      run,
      item.target.item,
    );
    if (window.location.hash === href) onSameAddress?.();
    else window.location.hash = href;
  };
  return (
    <>
      <button
        ref={field}
        type="button"
        aria-haspopup="dialog"
        aria-keyshortcuts="Control+K Meta+K"
        onClick={show}
        className="flex h-10 min-w-56 items-center gap-2 rounded-lg border border-border-control bg-surface-card px-3 text-body text-text-tertiary shadow-xs outline-hidden focus-visible:ring-2 focus-visible:ring-brand"
      >
        <SearchLg aria-hidden="true" className="size-4 flex-none" />
        <span className="grow text-left">{NAME}</span>
        <span className={KEY}>{shortcutLabel()}</span>
      </button>
      <ModalOverlay
        isOpen={open}
        onOpenChange={setOpen}
        isDismissable
        className="motion-reduce:animate-none sm:items-start sm:pt-[12vh]"
      >
        <Modal className="max-w-[640px] motion-reduce:animate-none">
          <Dialog aria-label={NAME}>
            <Autocomplete
              filter={(label, typed) => label.toLowerCase().includes(typed.toLowerCase())}
            >
              <SearchField
                aria-label="Search the items of this run"
                onKeyDown={(event) => {
                  // Escape always closes: the field would only clear what was typed.
                  if (event.key === "Escape") setOpen(false);
                }}
                className="flex h-14 items-center gap-2 border-b border-border-hairline px-4"
              >
                <SearchLg aria-hidden="true" className="size-5 flex-none text-text-tertiary" />
                <Input
                  ref={focusSearch}
                  className="min-w-0 grow bg-transparent text-md text-text-primary outline-hidden"
                />
                <span aria-hidden="true" className={KEY}>
                  {shortcutLabel()}
                </span>
              </SearchField>
              <ListBox
                aria-label="Items"
                onAction={go}
                renderEmptyState={() => (
                  <p className="px-4 py-6 text-center text-text-secondary">
                    {items.length === 0 ? "This run lists no item to jump to." : "No item matches"}
                  </p>
                )}
                className="max-h-[50vh] overflow-y-auto outline-hidden"
              >
                {JUMP_GROUPS.map((group) => {
                  const Icon = ICON[group];
                  return (
                    <ListBoxSection
                      key={group}
                      aria-label={group}
                      className="border-b border-border-hairline pb-2"
                    >
                      <Header className="mt-2 px-4.5 pt-2 pb-1 text-xs font-semibold text-text-tertiary">
                        {group}
                      </Header>
                      {items.flatMap((item, index) =>
                        item.group === group
                          ? [
                              <ListBoxItem
                                key={index}
                                id={String(index)}
                                textValue={item.label}
                                className="mx-2 flex min-h-10 cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-medium text-text-primary outline-hidden data-focused:bg-surface-subtle"
                              >
                                <Icon
                                  aria-hidden="true"
                                  className="size-4 flex-none text-text-tertiary"
                                />
                                {item.label}
                                <span className="font-normal text-text-tertiary">
                                  {item.detail}
                                </span>
                              </ListBoxItem>,
                            ]
                          : [],
                      )}
                    </ListBoxSection>
                  );
                })}
              </ListBox>
            </Autocomplete>
            <div className="flex h-13 items-center gap-4 px-4.5 text-sm font-semibold text-text-tertiary">
              <span>
                <span className={KEY}>↑↓</span> to move
              </span>
              <span>
                <span className={KEY}>↵</span> to open
              </span>
              <span>
                <span className={KEY}>esc</span> to close
              </span>
            </div>
          </Dialog>
        </Modal>
      </ModalOverlay>
    </>
  );
}
