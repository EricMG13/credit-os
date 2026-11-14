// A settings section: its h2 and hint line (the mock's `.sb h4` and the paragraph after it), an
// optional action at the right of the head, then the section's content.
import { useId, type ReactNode } from "react";

export function Section({
  title,
  hint,
  action,
  wide = false,
  children,
}: {
  title: string;
  hint: string;
  action?: ReactNode;
  /** The mock lets a table section use the full width (`max-width:none`). */
  wide?: boolean;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <section aria-labelledby={id} className={wide ? "min-w-0" : "min-w-0 max-w-[860px]"}>
      <div className="flex flex-wrap items-start gap-x-4 gap-y-2">
        <div>
          <h2 id={id} className="text-lg font-semibold text-text-primary">
            {title}
          </h2>
          <p className="mt-0.5 max-w-[72ch] text-sm text-text-tertiary">{hint}</p>
        </div>
        {action === undefined ? null : <div className="ml-auto">{action}</div>}
      </div>
      <div className="mt-6">{children}</div>
    </section>
  );
}
