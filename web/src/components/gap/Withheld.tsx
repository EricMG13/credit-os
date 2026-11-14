import { Badge } from "@/components/base/badges/badges";

export function Withheld({ reason }: { reason?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <span
          aria-hidden="true"
          className="withheld-stripes inline-block h-3 w-16 rounded-ds-full"
        />
        <Badge color="gray">Withheld</Badge>
      </div>
      {reason === undefined ? null : <p className="text-small text-text-secondary">{reason}</p>}
    </div>
  );
}
