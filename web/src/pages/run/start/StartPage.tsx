import { useId } from "react";
import { Button, styles } from "@/components/base/buttons/button";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { cx } from "@/utils/cx";
import { useSource } from "../../source";
import { readSlice, type StartDraft } from "../slice";
import { Confirm } from "./Confirm";
import { Context } from "./Context";
import { Documents } from "./Documents";
import { Purpose } from "./Purpose";
import { Readiness } from "./Readiness";
import { Stepper } from "./Stepper";

function LinkButton({
  href,
  primary,
  children,
}: {
  href: string;
  primary?: boolean;
  children: string;
}) {
  return (
    <a
      href={href}
      className={cx(
        styles.common.root,
        styles.sizes.md.root,
        styles.colors[primary === true ? "primary" : "secondary"].root,
      )}
    >
      <span data-text className="px-0.5">
        {children}
      </span>
    </a>
  );
}

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
        <LinkButton href={`#/run/start/${previous}`}>Previous</LinkButton>
      )}
      <span className="text-sm text-text-tertiary">{draft.position}</span>
      {draft.step === "start" ? null : (
        <div className="flex flex-wrap items-center gap-3">
          {nextBlocked === null ? null : (
            <span id={reasonId} className="text-sm text-text-secondary">
              {nextBlocked}
            </span>
          )}
          {next === null || nextBlocked !== null ? (
            <Button isDisabled aria-describedby={nextBlocked === null ? undefined : reasonId}>
              {draft.nextLabel}
            </Button>
          ) : (
            <LinkButton primary href={`#/run/start/${next}`}>
              {draft.nextLabel}
            </LinkButton>
          )}
        </div>
      )}
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
          <LinkButton href="#/run">Go to Run</LinkButton>
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
        <a href="#/" className="text-text-link underline">
          Library
        </a>
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
          {draft.step === "start" || draft.step === "started" ? (
            <h2 className="font-display text-h3 text-text-primary">
              {draft.step === "started" ? draft.title : "Start"}
            </h2>
          ) : null}
          {draft.step === "started" ? null : <Actions draft={draft} />}
        </div>
        <Readiness data={draft.readiness} />
      </div>
    </div>
  );
}
