import { useState } from "react";
import { CaseCards } from "./parts/CaseCards";
import { RunPage, runKey } from "./parts/RunPage";
import { StatementTable, type StatementView } from "./parts/StatementTable";
import { Bridges } from "./sections/Bridges";
import { CaseComparison } from "./sections/CaseComparison";
import { DebtSection } from "./sections/DebtSection";
import { RecoverySection } from "./sections/RecoverySection";
import type { ModelRun } from "./slice/types";

/** The case and the Figures or Bars choice are in-memory page state; the first case is default. */
function Body({ run }: { run: ModelRun }) {
  const [caseIndex, setCaseIndex] = useState(0);
  const [view, setView] = useState<StatementView>("figures");
  return (
    <>
      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-display text-h3 text-text-primary">Two cases</h2>
          <span className="text-small text-text-tertiary">
            Choose a case: the forecast columns and every chart below follow it.
          </span>
        </div>
        <CaseCards cases={run.cases} chosen={caseIndex} onChoose={setCaseIndex} />
      </section>
      <StatementTable page={run.statements} caseIndex={caseIndex} view={view} onView={setView} />
      <Bridges bridges={run.statements.bridges} caseIndex={caseIndex} />
      <CaseComparison data={run.statements.comparison} cases={run.cases} />
      <DebtSection stack={run.statements.debt.stack} maturities={run.statements.debt.maturities} />
      <RecoverySection
        recovery={run.statements.recovery}
        gap={run.statements.gap}
        checkFigure={run.statements.checkFigure}
        published={run.statements.published}
      />
    </>
  );
}

export function StatementsPage({ params }: { params: Record<string, string> }) {
  return (
    <RunPage params={params} current="statements">
      {(run) => <Body key={runKey(run)} run={run} />}
    </RunPage>
  );
}
