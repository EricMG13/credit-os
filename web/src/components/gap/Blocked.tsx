import { StatusBadge } from "@/components/status/StatusBadge";

export function Blocked({ reason }: { reason: string }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <StatusBadge set="Module state" state="Not assessable" />
      <p className="text-small text-text-secondary">{reason}</p>
    </div>
  );
}
