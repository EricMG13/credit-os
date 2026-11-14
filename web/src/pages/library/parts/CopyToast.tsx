import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { StatusShape } from "@/components/status/shapes";
import { cx } from "@/utils/cx";

/** How long the toast stays: one timer, started by the copy and cleared when the page leaves. */
const TOAST_MS = 4000;

type Outcome = { ok: boolean; title: string; text: string };

type Copy = (text: string, what: string) => Promise<void>;

const CopyContext = createContext<Copy | null>(null);

/**
 * Copies `text` for the snippet that asks and says what happened in the toast: "Copied", or
 * "Could not copy" in the error form when the browser refuses or has no clipboard (a page opened
 * from disk may). `what` names the thing, for example "The hash of annual-report-2026.pdf".
 */
export function useCopy(): Copy {
  const copy = useContext(CopyContext);
  if (copy === null) throw new Error("a snippet was drawn outside a CopyProvider");
  return copy;
}

/** The toast: success in the status form, a failure in the error form; static, nothing moves. */
function Toast({ outcome }: { outcome: Outcome }) {
  const tone = outcome.ok
    ? "border-success-edge bg-success-fill text-success-text"
    : "border-error-edge bg-error-fill text-error-text";
  return (
    <div
      role={outcome.ok ? "status" : "alert"}
      className={cx(
        "fixed right-8 bottom-8 z-50 flex max-w-md items-start gap-4 rounded-md border p-4 shadow-md",
        tone,
      )}
    >
      <span
        className={cx("mt-0.5 flex-none", outcome.ok ? "text-success-mark" : "text-error-mark")}
      >
        <StatusShape shape={outcome.ok ? "filled circle" : "diamond"} />
      </span>
      <div>
        <strong className="block text-md font-medium">{outcome.title}</strong>
        <p className="mt-0.5 text-sm">{outcome.text}</p>
      </div>
    </div>
  );
}

/** Holds the one toast of a page and the one timer that removes it. */
export function CopyProvider({ children }: { children: ReactNode }) {
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const timer = useRef<number | undefined>(undefined);
  useEffect(
    () => () => {
      window.clearTimeout(timer.current);
    },
    [],
  );
  const show = (next: Outcome) => {
    window.clearTimeout(timer.current);
    setOutcome(next);
    timer.current = window.setTimeout(() => {
      setOutcome(null);
    }, TOAST_MS);
  };
  const copy: Copy = async (text, what) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Shown, not swallowed: the reader is told nothing was copied.
      show({
        ok: false,
        title: "Could not copy",
        text: `${what} was not copied. Select it and copy it by hand.`,
      });
      return;
    }
    show({ ok: true, title: "Copied", text: `${what} is on your clipboard.` });
  };
  return (
    <CopyContext.Provider value={copy}>
      {children}
      {outcome === null ? null : <Toast outcome={outcome} />}
    </CopyContext.Provider>
  );
}
