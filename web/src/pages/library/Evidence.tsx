import { EvidenceSummary } from "./EvidenceSummary";
import { EvidenceFrame } from "./parts/EvidenceFrame";
import { RunFrame } from "./parts/RunFrame";

/** An Evidence page of a run: the run's frame, the Evidence frame with its tabs, then the page. */
export function Evidence({ issuer, run }: { issuer: string | undefined; run: string | undefined }) {
  return (
    <RunFrame issuer={issuer} run={run} tab="evidence">
      {({ evidence, id: runId }, issuerId) => (
        <EvidenceFrame issuer={issuerId} run={runId} evidence={evidence} current="summary">
          <EvidenceSummary evidence={evidence} issuer={issuerId} run={runId} />
        </EvidenceFrame>
      )}
    </RunFrame>
  );
}
