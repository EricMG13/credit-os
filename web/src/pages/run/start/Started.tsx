import { Alert } from "@/components/alert/Alert";
import { styles } from "@/components/base/buttons/button";
import { ProgressBar } from "@/components/base/progress-indicators/progress-indicators";
import { cx } from "@/utils/cx";
import type { StartDraft } from "../slice";

type Step = Extract<StartDraft, { step: "started" }>;

const GREY = "text-text-tertiary hover:text-text-secondary hover:*:data-text:decoration-current";

/** The mock's `lnk` (brand) or, with `grey`, its `lnk-g` secondary form. */
function TextLink({
  href,
  children,
  grey = false,
}: {
  href: string;
  children: string;
  grey?: boolean;
}) {
  return (
    <a
      href={href}
      className={cx(
        styles.common.root,
        styles.colors["link-color"].root,
        styles.sizes.md.linkRoot,
        grey && GREY,
      )}
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
      <Alert
        tone="info"
        title={draft.title}
        action={
          <div className="flex flex-col gap-3">
            <ProgressBar value={draft.cap.value} max={draft.cap.max} label={draft.cap.label} />
            <div className="flex flex-wrap gap-3">
              <TextLink href={`#/run/activity/${draft.activity}`}>Watch run activity</TextLink>
              <TextLink href="#/" grey>
                Back to the library
              </TextLink>
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
