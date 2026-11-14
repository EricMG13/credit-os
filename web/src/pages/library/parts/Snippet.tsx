import { Copy01 } from "@untitledui/icons";
import { ButtonUtility } from "@/components/base/buttons/button-utility";
import { useCopy } from "./CopyToast";

/**
 * A value to copy (R16): a caption, a card with its kind ("Code", "SHA-256") and a copy button, and
 * the value in full, wrapped, never cut. `what` names the value in the toast.
 */
export function Snippet({
  caption,
  kind,
  value,
  copyLabel,
  what,
}: {
  caption?: string;
  kind: string;
  value: string;
  copyLabel: string;
  what: string;
}) {
  const copy = useCopy();
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      {caption === undefined ? null : <span className="text-xs text-text-tertiary">{caption}</span>}
      <div className="overflow-hidden rounded-lg border border-border-hairline">
        <div className="flex items-center justify-between border-b border-border-hairline bg-surface-subtle p-1">
          <span className="m-0.75 rounded-lg bg-surface-card px-2 py-1 text-sm font-medium text-text-primary">
            {kind}
          </span>
          <ButtonUtility
            tooltip={copyLabel}
            icon={Copy01}
            className="size-9"
            onPress={() => {
              void copy(value, what);
            }}
          />
        </div>
        <pre className="m-0 bg-surface-card p-4 font-mono text-sm whitespace-pre-wrap break-all text-text-primary">
          {value}
        </pre>
      </div>
    </div>
  );
}
