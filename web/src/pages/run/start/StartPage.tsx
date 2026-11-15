import { useId } from "react";
import { Button } from "@/components/base/buttons/button";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { useSource } from "../../source";
import { TextLink } from "../TextLink";
import { readSlice, type StartDraft } from "../slice";
import { Confirm } from "./Confirm";
import { Context } from "./Context";
import { Documents } from "./Documents";
import { Purpose } from "./Purpose";
import { Readiness } from "./Readiness";
import { Start, Submit } from "./Start";
import { Started } from "./Started";
import { Stepper } from "./Stepper";

function Actions({ draft }: { draft: StartDraft }) {
  const reasonId = useId();
  const { previous, next, nextBlocked } = draft;
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
      {previous === null ? (
        <Button color="secondary" isDisabled>
          Previous
        </Button>
      ) : (
        <Button href={`#/run/start/${previous}`} color="secondary">
          Previous
        </Button>
      )}
      <span className="text-sm text-text-tertiary">{draft.position}</span>
      <div className="flex flex-wrap items-center gap-3">
        {nextBlocked === null ? null : (
          <span id={reasonId} className="text-sm text-text-secondary">
            {nextBlocked}
          </span>
        )}
        {draft.step === "start" ? (
          <Submit
            label={draft.nextLabel}
            confirm={draft.confirm}
            blocked={nextBlocked === null ? undefined : { id: reasonId }}
          />
        ) : (
          <>
            {next === null || nextBlocked !== null ? (
              <Button isDisabled aria-describedby={nextBlocked === null ? undefined : reasonId}>
                {draft.nextLabel}
              </Button>
            ) : (
              <Button href={`#/run/start/${next}`}>{draft.nextLabel}</Button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function Empty({ title, action }: { title: string; action?: boolean }) {
  return (
    <EmptyState>
      <EmptyState.Header>
        <EmptyState.FeaturedIcon />
      </EmptyState.Header>
      <EmptyState.Content>
        <EmptyState.Title>{title}</EmptyState.Title>
      </EmptyState.Content>
      {action === true ? (
        <EmptyState.Footer>
          <Button href="#/run" color="secondary">
            Go to Run
          </Button>
        </EmptyState.Footer>
      ) : null}
    </EmptyState>
  );
}

/** One snapshot of the run start: the step card (stepper, the step's panel, actions) and readiness. */
export function StartPage({ draft: id }: { draft: string }) {
  const slice = readSlice(useSource().run);
  if (slice.kind !== "ok") return <Empty title="No run data in this library" />;
  const draft = slice.data.drafts.find((d) => d.id === id);
  if (draft === undefined) return <Empty title="No draft has this address" action />;
  return (
    <div className="flex flex-col gap-4">
      <nav aria-label="Breadcrumb" className="text-sm text-text-tertiary">
        <TextLink href="#/">Library</TextLink>
        {` / ${draft.issuer} / New run`}
      </nav>
      <p className="text-body text-text-secondary">
        Add the documents, say what the run is for, approve what was read, then start. Nothing is
        spent before the last step.
      </p>
      <div className="grid items-start gap-6 min-[1041px]:grid-cols-[minmax(0,1fr)_320px]">
        <div className="flex flex-col gap-6 rounded-ds-lg border border-border-subtle bg-surface-card p-8 shadow-1">
          <Stepper step={draft.step} />
          {draft.step === "documents" ? <Documents files={draft.files} /> : null}
          {draft.step === "purpose" ? (
            <Purpose key={draft.id} chosen={draft.chosen} purposes={draft.purposes} />
          ) : null}
          {draft.step === "confirm" ? <Confirm groups={draft.groups} /> : null}
          {draft.step === "context" ? <Context key={draft.id} note={draft.note} /> : null}
          {draft.step === "start" ? <Start recap={draft.recap} paid={draft.paid} /> : null}
          {draft.step === "started" ? <Started issuer={draft.issuer} draft={draft} /> : null}
          {draft.step === "started" ? null : <Actions draft={draft} />}
        </div>
        <Readiness data={draft.readiness} />
      </div>
    </div>
  );
}
