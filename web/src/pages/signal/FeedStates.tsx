// What a feed shows instead of stories: the loading skeleton, the error alert and the empty states.
// Wording is the predecessor's (behaviour list 2.2); the layout follows mock states frames 2 to 7.
import { Star01 } from "@untitledui/icons";
import { Alert } from "@/components/alert/Alert";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { Button } from "@/components/base/buttons/button";
import { Skeleton } from "@/components/gap/Skeleton";

/** The three stories' skeleton: a tile and lines each, static, in the card's own frame. */
export function FeedSkeleton() {
  return (
    <section
      aria-label="Stories"
      aria-busy="true"
      className="mt-4 divide-y divide-border-hairline rounded-ds-lg border border-border-subtle bg-surface-card px-8 py-2 shadow-1"
    >
      <span className="sr-only">Loading stories</span>
      {[4, 4, 3].map((lines, index) => (
        <div key={index} data-skeleton-story className="flex gap-4 py-6">
          <div aria-hidden="true" className="size-20 shrink-0 rounded-ds-xs bg-surface-subtle" />
          <div className="min-w-0 flex-1">
            <Skeleton lines={lines} />
          </div>
        </div>
      ))}
    </section>
  );
}

type FeedError = "unreachable" | "request" | "unreadable";

const SENTENCES: Record<FeedError, string> = {
  unreachable: "Signal could not be reached. Check your connection and try again.",
  request: "Signal could not complete that request.",
  unreadable: "The service sent an unreadable answer.",
};

/** Retry has no service to call in the sample, so it is drawn disabled with its reason in view. */
export function FeedAlert({ error }: { error: FeedError }) {
  return (
    <div className="mt-4">
      <Alert
        tone="error"
        title={SENTENCES[error]}
        action={
          <div className="flex flex-wrap items-center gap-3">
            <Button color="secondary" size="sm" isDisabled aria-describedby="feed-retry-reason">
              Retry
            </Button>
            <span id="feed-retry-reason" className="text-sm text-error-text">
              Sample data: there is no service to retry.
            </span>
          </div>
        }
      />
    </div>
  );
}

/** What the empty state of a view needs: which view, the source state and the follow state. */
export type EmptyContext = {
  view: "for-you" | "latest" | "saved" | "topic";
  approved: boolean;
  /** Where a writer proposes a source; a reader has none. */
  propose: string | null;
  /** True when the slice holds no followed topic (the For you wording). */
  noneFollowed: boolean;
  topics: { id: string; name: string; on: boolean }[];
  onFollow: (id: string) => void;
};

type Words = { title: string; hint: string | null };

/** First match wins: no approved source, For you with nothing followed, Saved, a topic, otherwise. */
function wordsFor(context: EmptyContext): Words {
  if (!context.approved)
    return { title: "No approved sources yet", hint: "Stories appear once a source is approved." };
  if (context.view === "for-you" && context.noneFollowed)
    return {
      title: "Follow a topic to fill this view",
      hint: "Stories on the topics you follow appear here.",
    };
  if (context.view === "saved")
    return { title: "Stories you save appear here", hint: "Use Save on a story to keep it." };
  if (context.view === "topic") return { title: "No stories in this topic yet", hint: null };
  return { title: "No stories yet", hint: "New stories appear here as sources are checked." };
}

export function FeedEmpty({ context }: { context: EmptyContext }) {
  const { title, hint } = wordsFor(context);
  const follow = context.approved && context.view === "for-you" && context.noneFollowed;
  return (
    <EmptyState className="mt-4 py-12">
      <EmptyState.Header>
        <EmptyState.FeaturedIcon />
      </EmptyState.Header>
      <EmptyState.Content>
        <EmptyState.Title>{title}</EmptyState.Title>
        {hint === null ? null : <EmptyState.Description>{hint}</EmptyState.Description>}
      </EmptyState.Content>
      {!context.approved && context.propose !== null ? (
        <EmptyState.Footer>
          <a className="text-sm font-semibold text-text-link" href={context.propose}>
            Propose a source
          </a>
        </EmptyState.Footer>
      ) : null}
      {follow ? (
        <EmptyState.Footer className="flex-wrap justify-center">
          {context.topics.map((topic) => (
            <Button
              key={topic.id}
              color="secondary"
              size="md"
              aria-pressed={topic.on}
              aria-label={`${topic.on ? "Unfollow" : "Follow"} ${topic.name}`}
              iconLeading={<Star01 data-icon className={topic.on ? "fill-current" : undefined} />}
              onPress={() => {
                context.onFollow(topic.id);
              }}
            >
              {topic.name}
            </Button>
          ))}
        </EmptyState.Footer>
      ) : null}
    </EmptyState>
  );
}
