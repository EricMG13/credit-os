// A digest in the feed (mock `.st` with the digest meta row): "Digest" label, "AI" label when a model
// wrote it, the name, the date and an unread mark; the title, the numbered points, the delivered
// summary and a link to the digest. A nothing-to-report card is one sentence: no points, no AI label,
// no link, since no model made it.
import { ArrowRight } from "@untitledui/icons";
import { Badge } from "@/components/base/badges/badges";
import { MediaObject } from "./parts/MediaObject";
import { NumberedPanel } from "./parts/NumberedPanel";
import type { SignalDigestCard } from "./slice";

const FOCUS = "outline-focus-ring focus-visible:outline-2";

export function DigestCard({ digest, href }: { digest: SignalDigestCard; href: string }) {
  const { title } = digest;
  return (
    <article className="py-6">
      <MediaObject tile={digest.monogram}>
        <div className="mb-1.5 flex flex-wrap items-center gap-2 text-sm text-text-tertiary">
          <Badge size="sm">Digest</Badge>
          {digest.ai ? <Badge size="sm">AI</Badge> : null}
          <span>{digest.digestName}</span>
          {digest.date === null ? null : <span>{digest.date}</span>}
          {digest.unread ? (
            <>
              <span aria-hidden="true" className="size-2 rounded-full bg-action" />
              <span>Unread</span>
            </>
          ) : null}
        </div>
        {digest.nothing === null ? (
          <>
            <h2 tabIndex={-1} className="text-lg font-medium text-text-primary">
              <a href={href} className={`text-text-primary hover:underline ${FOCUS}`}>
                {title}
              </a>
            </h2>
            <div className="mt-3">
              <NumberedPanel items={digest.points} />
            </div>
            {digest.summary === null ? null : (
              <p className="mt-3 text-sm text-text-tertiary">{digest.summary}</p>
            )}
            <div className="mt-3">
              <a
                href={href}
                aria-label={`Read the digest: ${title}`}
                className={`inline-flex items-center gap-1 text-sm font-semibold text-text-link ${FOCUS}`}
              >
                Read the digest
                <ArrowRight aria-hidden="true" className="size-4" />
              </a>
            </div>
          </>
        ) : (
          <>
            <h2 tabIndex={-1} className="text-lg font-medium text-text-primary">
              {title}
            </h2>
            <p className="mt-0.5 max-w-[72ch] text-text-secondary">{digest.nothing}</p>
          </>
        )}
      </MediaObject>
    </article>
  );
}
