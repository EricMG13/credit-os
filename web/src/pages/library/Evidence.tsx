import { useState } from "react";
import { EvidenceSources } from "./EvidenceSources";
import { EvidenceSummary } from "./EvidenceSummary";
import type { LoadedRun } from "./slice";
import { EvidenceFrame, type EvidenceTab } from "./parts/EvidenceFrame";
import { ALL, FilterSelect } from "./parts/FilterBar";
import { RunFrame } from "./parts/RunFrame";

/**
 * Sources with its module filter, which the frame draws at the heading's right. The filter is page
 * state, in memory; its options are the delivered module names, and what is compared is the id.
 */
function SourcesPage({ run, issuer }: { run: LoadedRun; issuer: string }) {
  const [name, setName] = useState(ALL);
  const { evidence } = run;
  const chosen = evidence.moduleFilter.find((option) => option.name === name) ?? null;
  return (
    <EvidenceFrame
      issuer={issuer}
      run={run.id}
      evidence={evidence}
      current="sources"
      filter={
        <FilterSelect
          name="Module"
          options={evidence.moduleFilter.map((option) => option.name)}
          value={name}
          onChange={setName}
        />
      }
    >
      <EvidenceSources
        sources={evidence.sources}
        module={chosen?.id ?? null}
        moduleName={chosen?.name ?? null}
        onClear={() => {
          setName(ALL);
        }}
      />
    </EvidenceFrame>
  );
}

/** An Evidence page of a run: the run's frame, the Evidence frame with its tabs, then the page. */
export function Evidence({
  issuer,
  run,
  page,
}: {
  issuer: string | undefined;
  run: string | undefined;
  page: Extract<EvidenceTab, "summary" | "sources">;
}) {
  return (
    <RunFrame issuer={issuer} run={run} tab="evidence">
      {(loaded, issuerId) =>
        page === "sources" ? (
          <SourcesPage run={loaded} issuer={issuerId} />
        ) : (
          <EvidenceFrame
            issuer={issuerId}
            run={loaded.id}
            evidence={loaded.evidence}
            current="summary"
          >
            <EvidenceSummary evidence={loaded.evidence} issuer={issuerId} run={loaded.id} />
          </EvidenceFrame>
        )
      }
    </RunFrame>
  );
}
