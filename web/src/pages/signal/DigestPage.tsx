// The digest page (mock digests frames 1, 3 and 4). A digest that is running and has an issue: a meta
// line (Digest, AI where a model wrote it, the digest's name, the date), the newest issue's title as the
// page's h1, its delivered summary and its numbered points (each with the stories behind it, linked to
// their sources where the address is a web one; no article text). An issue with nothing material is
// the kit's empty state instead of the list. "Earlier digests" is a card of rows, one per earlier
// issue (not links: no page holds one issue). A paused digest says so in an info alert, takes its own
// name as the h1 and draws every issue as a row. The column is the mock's 820px.
import { useRef, type ReactNode } from "react";
import { Alert } from "@/components/alert/Alert";
import { Badge } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { StatusBadge } from "@/components/status/StatusBadge";
import { MediaObject } from "./parts/MediaObject";
import { NumberedPanel } from "./parts/NumberedPanel";
import { PageTitle } from "./parts/PageTitle";
import { sceneHref } from "./SignalFrame";
import type { SignalDigest, SignalDigestIssue, SignalScene } from "./slice";
import { isWebLink } from "./StoryCard";

const FOCUS = "outline-focus-ring focus-visible:outline-2";
const META = "mb-1.5 flex flex-wrap items-center gap-2 text-sm text-text-tertiary";

type Point = SignalDigestIssue["points"][number];

function Stories({ point }: { point: Point }) {
  return (
    <>
      {point.storiesLine === null ? null : (
        <p className="mt-2.5 text-sm text-text-tertiary">{point.storiesLine}</p>
      )}
      {point.stories.length === 0 ? null : (
        <ul
          aria-label={`Stories behind: ${point.lead}`}
          className="mt-1 flex flex-col gap-1 text-sm text-text-tertiary"
        >
          {point.stories.map((story, index) => {
            const link = story.url !== null && isWebLink(story.url) ? story.url : null;
            const rest = `, ${story.source}${story.time === null ? "" : `, ${story.time}`}`;
            return (
              <li key={index}>
                {link === null ? (
                  `${story.headline}${rest} (no link)`
                ) : (
                  <>
                    <a
                      href={link}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Open source: ${story.headline} (opens in a new tab)`}
                      className={`font-medium text-text-link hover:underline ${FOCUS}`}
                    >
                      {story.headline}
                    </a>
                    {rest}
                  </>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}

/** The newest issue's body: its points, or the empty state when nothing was material. */
function Body({
  issue,
  hasEarlier,
  onEarlier,
}: {
  issue: SignalDigestIssue;
  hasEarlier: boolean;
  onEarlier: () => void;
}) {
  if (issue.nothing !== null) {
    return (
      <EmptyState className="py-12">
        <EmptyState.Header>
          <EmptyState.FeaturedIcon />
        </EmptyState.Header>
        <EmptyState.Content>
          <EmptyState.Title>Nothing material to report</EmptyState.Title>
          <EmptyState.Description>{issue.nothing}</EmptyState.Description>
        </EmptyState.Content>
        {hasEarlier ? (
          <EmptyState.Footer>
            <Button color="secondary" onPress={onEarlier}>
              See earlier digests
            </Button>
          </EmptyState.Footer>
        ) : null}
      </EmptyState>
    );
  }
  if (issue.points.length === 0) return null;
  return (
    <div className="mt-5">
      <NumberedPanel
        leadAs="h2"
        items={issue.points.map((point) => ({
          number: point.number,
          lead: point.lead,
          body: point.body,
          children: <Stories point={point} />,
        }))}
      />
    </div>
  );
}

/** An earlier issue as a row (frame 4): tile, labels, date, title as an h3 carrying the issue's id, and its delivered line. */
function Row({ digest, issue }: { digest: SignalDigest; issue: SignalDigestIssue }) {
  return (
    <li className="py-6">
      <MediaObject tile={digest.monogram}>
        <div className={META}>
          <Badge size="sm">Digest</Badge>
          {issue.ai ? <Badge size="sm">AI</Badge> : null}
          {issue.date === null ? null : <span>{issue.date}</span>}
        </div>
        <h3 id={issue.id} className="text-lg font-medium text-text-primary">
          {issue.title}
        </h3>
        {/* Keyed by slot, not by text: the summary and the nothing line may be the same sentence. */}
        {(
          [
            ["summary", issue.summary],
            ["nothing", issue.nothing],
          ] as const
        ).map(([slot, line]) =>
          line === null ? null : (
            <p key={slot} className="mt-0.5 max-w-[72ch] text-sm text-text-tertiary">
              {line}
            </p>
          ),
        )}
      </MediaObject>
    </li>
  );
}

/** `none` is the empty state a digest with no issue draws (the page that owns the empty states passes it). */
export function DigestPage({
  scene,
  digest,
  writer,
  none,
}: {
  scene: SignalScene;
  /** A reader's Settings holds Topics and Notifications only (ruling 18), so only a writer is sent to AI and cost. */
  writer: boolean;
  digest: SignalDigest;
  none: ReactNode;
}) {
  const earlierTitle = useRef<HTMLHeadingElement>(null);
  const [first, ...rest] = digest.issues;
  // A paused digest writes no new issue: every issue is an earlier one.
  const current = digest.paused === null ? first : undefined;
  const earlier = current === undefined ? digest.issues : rest;
  return (
    <div className="max-w-[820px]">
      {current === undefined ? (
        <div className="flex flex-wrap items-center gap-3">
          <PageTitle>{digest.name}</PageTitle>
          {digest.paused === null ? null : (
            <StatusBadge set="Signal source states" state="Paused" />
          )}
        </div>
      ) : (
        <>
          <div className={META}>
            <Badge size="sm">Digest</Badge>
            {current.ai ? <Badge size="sm">AI</Badge> : null}
            <span>{digest.name}</span>
            {current.date === null ? null : <span>{current.date}</span>}
          </div>
          <PageTitle>{current.title}</PageTitle>
          {current.summary === null ? null : (
            <p className="mt-1 max-w-[72ch] text-sm text-text-tertiary">{current.summary}</p>
          )}
        </>
      )}
      {digest.paused === null ? null : (
        <div className="mt-4">
          <Alert
            tone="info"
            title={digest.paused}
            action={
              writer ? (
                <a
                  href={sceneHref(scene, "settings/ai")}
                  className={`text-sm font-semibold text-text-link ${FOCUS}`}
                >
                  Open AI and cost
                </a>
              ) : undefined
            }
          />
        </div>
      )}
      {digest.issues.length === 0 ? none : null}
      {current === undefined ? null : (
        <Body
          issue={current}
          hasEarlier={earlier.length > 0}
          onEarlier={() => {
            earlierTitle.current?.focus();
          }}
        />
      )}
      {earlier.length === 0 ? null : (
        <section className="mt-8">
          <h2
            ref={earlierTitle}
            tabIndex={-1}
            className={`mb-3 text-lg font-semibold text-text-primary ${FOCUS}`}
          >
            Earlier digests
          </h2>
          <ul className="divide-y divide-border-hairline rounded-ds-lg border border-border-subtle bg-surface-card px-8 py-2 shadow-1">
            {earlier.map((issue) => (
              <Row key={issue.id} digest={digest} issue={issue} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
