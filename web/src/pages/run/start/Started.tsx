import { Alert } from "@/components/alert/Alert";
import { styles } from "@/components/base/buttons/button";
import { ProgressBar } from "@/components/base/progress-indicators/progress-indicators";
import { cx } from "@/utils/cx";
import type { StartDraft } from "../slice";

type Step = Extract<StartDraft, { step: "started" }>;

function TextLink({ href, children }: { href: string; children: string }) {
  return (
    <a
      href={href}
      className={cx(styles.common.root, styles.colors["link-color"].root, styles.sizes.md.linkRoot)}
    >
      <span data-text>{children}</span>
    </a>
  );
}

/** The Run started panel: the info alert holds the cap bar and the two links (the kit Alert's
 *  action slot takes any node), and a line on closing the page. Nothing animates. */
export function Started({ issuer, draft }: { issuer: string; draft: Step }) {
  return (
    <div className="flex flex-col gap-4">
      <h2 className="sr-only">{draft.title}</h2>
      <Alert
        tone="info"
        title={draft.title}
        action={
          <div className="flex flex-col gap-3">
            <ProgressBar value={draft.cap.value} max={draft.cap.max} label={draft.cap.label} />
            <div className="flex flex-wrap gap-3">
              <TextLink href={`#/run/activity/${draft.activity}`}>Watch run activity</TextLink>
              <TextLink href="#/">Back to the library</TextLink>
            </div>
          </div>
        }
      >
        {draft.text}
      </Alert>
      <p className="text-sm text-text-tertiary">
        You can close this page. The run carries on, and its library appears under {issuer} when it
        finishes.
      </p>
    </div>
  );
}
