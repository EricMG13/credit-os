import { StatusBadge } from "@/components/status/StatusBadge";
import type { StartDraft } from "../slice";
import { DetailsList } from "./DetailsList";

type Groups = Extract<StartDraft, { step: "confirm" }>["groups"];

/** The Confirm step: what was read and what will run, one details list per group. */
export function Confirm({ groups }: { groups: Groups }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h2 className="font-display text-h3 text-text-primary">Confirm what was read</h2>
          <p className="text-sm text-text-secondary">
            This is what the documents say and what will run. Approving it costs nothing.
          </p>
        </div>
        <StatusBadge set="Approval" state="Awaiting your approval" />
      </div>
      <div className="flex flex-col gap-7">
        {groups.map((group) => (
          <section key={group.name} className="flex flex-col gap-2">
            <h3 className="text-xs font-medium text-text-tertiary">{group.name}</h3>
            <DetailsList rows={group.rows} />
          </section>
        ))}
      </div>
    </div>
  );
}
