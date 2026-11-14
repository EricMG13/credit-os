import { cx } from "@/utils/cx";
import type { BottomLineText } from "../slice";
import { TRACE_HOST, TraceControl } from "./TraceControl";

type Level = "h2" | "h3" | "h4";

/**
 * The navy bottom-line band (P1): label, the lead in the h3 size, the rest and one trace control.
 * `level` is the heading level of the lead, so module pages can reuse the band under their own.
 */
export function BottomLine({ text, level }: { text: BottomLineText; level: Level }) {
  const Lead = level;
  return (
    <section
      aria-label={text.label}
      className={cx(
        TRACE_HOST,
        "flex items-start gap-4 rounded-[10px] bg-surface-inverse px-8 py-6 text-white",
      )}
    >
      <span
        aria-hidden="true"
        className="mt-0.5 flex size-6.5 flex-none items-center justify-center rounded-ds-full border border-white/20 bg-white/10 shadow-sm"
      >
        <span className="size-2 rounded-ds-full bg-white" />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <span className="text-sm font-medium text-brand-100">{text.label}</span>
        <Lead className="font-display text-h3">{text.lead}</Lead>
        <p className="max-w-[76ch] text-body">{text.rest}</p>
      </div>
      <TraceControl trace={text.trace} label="Show sources for the bottom line" onDark />
    </section>
  );
}
