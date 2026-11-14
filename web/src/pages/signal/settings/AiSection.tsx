// Settings, AI and cost (mock settings frames 7, 8 and 9): an alert when AI is off or at its cap,
// the spend against the cap as the kit's progress bar with the delivered label, and a switch per
// AI part showing its delivered state. The switches are disabled in every scene, with the reason in
// view (decision 0006 ruling 21: nothing here calls a model or writes). The bar's position places
// it only; no percentage is drawn.
import { Alert } from "@/components/alert/Alert";
import { ProgressBar } from "@/components/base/progress-indicators/progress-indicators";
import type { SignalAi } from "../slice";
import { Toggle } from "../parts/Toggle";
import { Section } from "./Section";

const REASON_ID = "signal-ai-parts-reason";
const INTRO_ON =
  "Opening or refreshing a page never calls a model. These parts do, when a story arrives or a digest is due.";
const INTRO_STOPPED = "Opening or refreshing a page never calls a model.";

export function AiSection({ ai }: { ai: SignalAi }) {
  const { state, notice, spend, parts } = ai;
  return (
    <Section title="AI and cost" hint={state === "on" ? INTRO_ON : INTRO_STOPPED}>
      <div className="flex max-w-[640px] flex-col gap-6">
        {notice === null ? null : (
          <Alert tone={state === "capped" ? "warning" : "info"} title={notice.title}>
            {notice.text}
          </Alert>
        )}
        <div>
          <span className="text-sm font-medium text-text-secondary">
            {spend === null ? "Spend" : spend.title}
          </span>
          <div className="mt-2">
            {spend === null ? (
              <span className="text-sm text-text-tertiary">n.a.</span>
            ) : (
              <ProgressBar value={spend.position} max={1} label={spend.label} />
            )}
          </div>
          {spend === null || spend.note === null ? null : (
            <p className="mt-1.5 text-sm text-text-tertiary">{spend.note}</p>
          )}
        </div>
        {parts.length === 0 ? null : (
          <>
            <p id={REASON_ID} className="-mb-2 text-sm text-text-tertiary">
              AI parts stay off until the owner sets a cap.
            </p>
            <ul className="flex flex-col gap-5">
              {parts.map((part) => (
                <li key={part.id}>
                  <Toggle
                    label={part.label}
                    hint={part.hint}
                    isSelected={part.on}
                    isDisabled
                    aria-describedby={REASON_ID}
                  />
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </Section>
  );
}
