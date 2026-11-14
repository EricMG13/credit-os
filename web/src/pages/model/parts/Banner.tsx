import type { ReactNode } from "react";

/** A Navy band with white text: the lead at h3 size, the rest below, an optional trace control. */
export function Banner({
  lead,
  children,
  trace,
}: {
  lead: string;
  children: string;
  trace: ReactNode;
}) {
  return (
    <div className="group/trace flex items-start gap-4 rounded-ds-md bg-surface-inverse px-6 py-5 text-text-on-action">
      <span
        aria-hidden="true"
        className="mt-0.5 flex size-7 flex-none items-center justify-center rounded-ds-sm bg-white/15"
      >
        <i className="size-3 rounded-full bg-text-on-action" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="max-w-[72ch] font-display text-h3 text-balance">{lead}</p>
        <p className="mt-2 max-w-[78ch] text-body text-text-on-action/80">{children}</p>
      </div>
      {trace}
    </div>
  );
}
