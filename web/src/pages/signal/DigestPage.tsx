// The digest page (mock digests frames 1, 3 and 4). The digest's name is the page's h1. The newest
// issue is drawn in full as an h2 section, every earlier issue in full under "Earlier digests", so any
// feed card's issue is on the page. Each point has its delivered number, bold lead, body and the
// stories behind it, linked to their sources where the address is a web one; no article text. An
// issue with nothing material is its one delivered sentence with no list and no AI label. A paused
// digest says so in an info alert and keeps every issue readable.
import type { ReactNode } from "react";
import { Alert } from "@/components/alert/Alert";
import { Badge } from "@/components/base/badges/badges";
import { StatusBadge } from "@/components/status/StatusBadge";
import { NumberedPanel } from "./parts/NumberedPanel";
import { PageTitle } from "./parts/PageTitle";
import type { SignalDigest, SignalDigestIssue } from "./slice";
import { isWebLink } from "./StoryCard";

const FOCUS = "outline-focus-ring focus-visible:outline-2";

type Story = SignalDigestIssue["points"][number]["stories"][number];

function Stories({ lead, stories }: { lead: string; stories: Story[] }) {
  if (stories.length === 0) return null;
  return (
    <ul
      aria-label={`Stories behind: ${lead}`}
      className="mt-2.5 flex flex-col gap-1 text-sm text-text-tertiary"
    >
      {stories.map((story, index) => (
        <li key={index}>
          {story.url !== null && isWebLink(story.url) ? (
            <a
              href={story.url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Open source: ${story.headline} (opens in a new tab)`}
              className={`font-medium text-text-link hover:underline ${FOCUS}`}
            >
              {story.headline}
            </a>
          ) : (
            story.headline
          )}
          {`, ${story.source}`}
          {story.time === null ? null : `, ${story.time}`}
        </li>
      ))}
    </ul>
  );
}

/** One issue as a section whose heading carries the issue's id; `level` is its heading's level. */
function Issue({ issue, level }: { issue: SignalDigestIssue; level: 2 | 3 }) {
  const Title = level === 2 ? "h2" : "h3";
  return (
    <section aria-labelledby={issue.id} className="mt-6">
      <div className="mb-1.5 flex flex-wrap items-center gap-2 text-sm text-text-tertiary">
        <Badge size="sm">Digest</Badge>
        {issue.ai ? <Badge size="sm">AI</Badge> : null}
        {issue.date === null ? null : <span>{issue.date}</span>}
      </div>
      <Title id={issue.id} className="text-lg font-semibold text-text-primary">
        {issue.title}
      </Title>
      {issue.summary === null ? null : (
        <p className="mt-1 max-w-[72ch] text-sm text-text-tertiary">{issue.summary}</p>
      )}
      {issue.nothing === null ? (
        <div className="mt-4">
          <NumberedPanel
            leadAs={level === 2 ? "h3" : "h4"}
            items={issue.points.map((point) => ({
              number: point.number,
              lead: point.lead,
              body: point.body,
              children: <Stories lead={point.lead} stories={point.stories} />,
            }))}
          />
        </div>
      ) : (
        <p className="mt-2 max-w-[72ch] text-text-secondary">{issue.nothing}</p>
      )}
    </section>
  );
}

/** `none` is the empty state a digest with no issue draws (the page that owns the empty states passes it). */
export function DigestPage({ digest, none }: { digest: SignalDigest; none: ReactNode }) {
  const paused = digest.paused !== null;
  const [newest, ...before] = digest.issues;
  // A paused digest writes no new issue: all of them are earlier ones.
  const earlier = paused ? digest.issues : before;
  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <PageTitle>{digest.name}</PageTitle>
        {paused ? <StatusBadge set="Signal source states" state="Paused" /> : null}
      </div>
      {digest.paused === null ? null : (
        <div className="mt-4">
          <Alert tone="info" title={digest.paused} />
        </div>
      )}
      {newest === undefined ? none : null}
      {paused || newest === undefined ? null : <Issue issue={newest} level={2} />}
      {earlier.length === 0 ? null : (
        <section className="mt-8">
          <h2 className="text-lg font-semibold text-text-primary">Earlier digests</h2>
          {earlier.map((issue) => (
            <Issue key={issue.id} issue={issue} level={3} />
          ))}
        </section>
      )}
    </>
  );
}
