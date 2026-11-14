import { StatusShape } from "@/components/status/shapes";

const GAP_WORDS = "Not established for this run";

export function GapPanel({ reason }: { reason: string }) {
  return (
    <div className="gap-hatch flex flex-col gap-2 rounded-ds-md border border-dashed border-border-gap p-4 text-gap-text">
      <p className="flex items-center gap-2 text-body font-semibold">
        <StatusShape shape="dashed ring" />
        {GAP_WORDS}
      </p>
      <p className="text-small">{reason}</p>
    </div>
  );
}
