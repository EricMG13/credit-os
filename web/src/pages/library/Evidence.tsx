import type { ReactNode } from "react";
import { EvidenceGaps } from "./EvidenceGaps";
import { EvidenceSources } from "./EvidenceSources";
import { EvidenceSummary } from "./EvidenceSummary";
import { EvidenceTrace } from "./EvidenceTrace";
import type { LoadedRun, Reader } from "./slice";
import { EvidenceFrame, type EvidenceTab } from "./parts/EvidenceFrame";
import { useModuleFilter } from "./parts/ModuleFilter";
import { RunFrame } from "./parts/RunFrame";

/**
 * A tab whose content is delivered per module draws the module filter at the heading's right. The
 * filter is state of the tab: the caller keys this by the tab, so each starts at "All".
 */
function FilteredTab({
  run,
  issuer,
  current,
  children,
}: {
  run: LoadedRun;
  issuer: string;
  current: Extract<EvidenceTab, "sources" | "trace" | "gaps">;
  children: (module: Reader | null, clear: () => void) => ReactNode;
}) {
  const { chosen, clear, control } = useModuleFilter(run.evidence.moduleFilter);
  return (
    <EvidenceFrame
      issuer={issuer}
      run={run.id}
      evidence={run.evidence}
      current={current}
      filter={control}
    >
      {children(chosen, clear)}
    </EvidenceFrame>
  );
}

/** An Evidence page of a run: the run's frame, the Evidence frame with its tabs, then the page. */
export function Evidence({
  issuer,
  run,
  page,
  item,
}: {
  issuer: string | undefined;
  run: string | undefined;
  page: Extract<EvidenceTab, "summary" | "sources" | "trace" | "gaps">;
  /** The trace item the address names, on the Trace page only. */
  item?: string | undefined;
}) {
  return (
    <RunFrame issuer={issuer} run={run} tab="evidence">
      {(loaded, issuerId) => {
        const { evidence } = loaded;
        switch (page) {
          case "sources":
            return (
              <FilteredTab key="sources" run={loaded} issuer={issuerId} current="sources">
                {(chosen, clear) => (
                  <EvidenceSources sources={evidence.sources} module={chosen} onClear={clear} />
                )}
              </FilteredTab>
            );
          case "trace":
            return (
              <FilteredTab key="trace" run={loaded} issuer={issuerId} current="trace">
                {(chosen, clear) => (
                  <EvidenceTrace
                    key={item ?? ""}
                    table={evidence.trace}
                    count={evidence.tabs.trace}
                    module={chosen}
                    onClear={clear}
                    item={item ?? null}
                  />
                )}
              </FilteredTab>
            );
          case "gaps":
            return (
              <FilteredTab key="gaps" run={loaded} issuer={issuerId} current="gaps">
                {(chosen, clear) => (
                  <EvidenceGaps
                    table={evidence.gaps}
                    count={evidence.tabs.gaps}
                    module={chosen}
                    onClear={clear}
                    issuer={issuerId}
                    run={loaded.id}
                  />
                )}
              </FilteredTab>
            );
          case "summary":
            return (
              <EvidenceFrame
                issuer={issuerId}
                run={loaded.id}
                evidence={evidence}
                current="summary"
              >
                <EvidenceSummary evidence={evidence} issuer={issuerId} run={loaded.id} />
              </EvidenceFrame>
            );
        }
      }}
    </RunFrame>
  );
}
