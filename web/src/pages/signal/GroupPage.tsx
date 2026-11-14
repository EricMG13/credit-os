// The group view (mock frames "Group view, writer" and "Group view, reader"): the group and its
// members, then what was shared on one card with hairlines. A story is drawn with the story card
// and a note with its sharer's avatar and line; each has an "Open thread" link. The thread route draws
// this view under the thread panel. Nothing here writes: New thread and
// Attach story are present for a writer and disabled with their reason in view.
import { Link01, Users01, MessageSquare01, Plus } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { Button } from "@/components/base/buttons/button";
import { sceneHref } from "./SignalFrame";
import { StoryCard } from "./StoryCard";
import { ArchivedBadge } from "./parts/ArchivedBadge";
import { Avatar } from "./parts/Avatar";
import { AvatarGroup } from "./parts/AvatarGroup";
import { PageTitle } from "./parts/PageTitle";
import type { SignalGroup, SignalScene, SignalStory, SignalThreadSummary } from "./slice";

const REASON_ID = "signal-group-write-reason";
const FOCUS = "outline-focus-ring focus-visible:outline-2";

function Header({ group, writer }: { group: SignalGroup; writer: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
      <div className="flex items-center gap-3">
        <Avatar size="md" initials={null} icon={Users01} />
        <div>
          <PageTitle>{group.name}</PageTitle>
          <p className="text-sm text-text-tertiary">
            <span>{group.memberSummary}</span>
            {" · "}
            <span>{group.visibility}</span>
          </p>
        </div>
      </div>
      {group.members.length === 0 ? null : (
        <>
          <AvatarGroup monograms={group.members.map((m) => m.initials)} more={group.moreMembers} />
          <ul aria-label="Members" className="sr-only">
            {group.members.map((m) => (
              <li key={m.name}>{m.name}</li>
            ))}
          </ul>
        </>
      )}
      {writer ? (
        <div className="ml-auto flex flex-wrap items-center justify-end gap-3">
          {/* They would write; the sample has no service, so they are disabled with the reason beside them. */}
          <Button color="secondary" iconLeading={Link01} isDisabled aria-describedby={REASON_ID}>
            Attach story
          </Button>
          <Button color="primary" iconLeading={Plus} isDisabled aria-describedby={REASON_ID}>
            New thread
          </Button>
          <span id={REASON_ID} className="basis-full text-right text-sm text-text-tertiary">
            Sample data: threads cannot be started here.
          </span>
        </div>
      ) : null}
    </div>
  );
}

/** A note: the sharer's avatar and line, then the text. Human text, so it may sit in a bubble. */
function Note({ thread }: { thread: SignalThreadSummary }) {
  if (thread.note === null) throw new Error("a note item holds no note");
  return (
    <article className="flex items-start gap-3 py-6">
      <Avatar size="sm" initials={thread.sharedBy.initials} />
      <div className="min-w-0 flex-1">
        <h2 className="text-sm font-semibold text-text-primary">{thread.sharedBy.label}</h2>
        <p className="mt-2 max-w-[72ch] rounded-ds-sm border border-border-hairline bg-surface-subtle px-3 py-2 text-text-primary">
          {thread.note}
        </p>
      </div>
    </article>
  );
}

function Item({
  scene,
  group,
  thread,
  story,
  writer,
}: {
  scene: SignalScene;
  group: SignalGroup;
  thread: SignalThreadSummary;
  story: SignalStory | null;
  writer: boolean;
}) {
  return (
    <li>
      {story === null ? (
        <Note thread={thread} />
      ) : (
        // The thread's own sharer line and count replace the feed's; its count sits in the footer.
        <StoryCard
          story={{ ...story, sharedBy: thread.sharedBy, commentCount: null }}
          scene={scene}
          writer={writer}
          inGroup
        />
      )}
      <div className="-mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 pb-5 text-sm text-text-tertiary sm:pl-24">
        {story !== null && thread.note !== null ? (
          <p className="basis-full text-text-secondary">{thread.note}</p>
        ) : null}
        {thread.unread ? (
          <span className="inline-flex items-center gap-1.5">
            <span aria-hidden="true" className="size-2 rounded-full bg-action" />
            <span className="sr-only">Unread</span>
          </span>
        ) : null}
        {thread.archived ? <ArchivedBadge /> : null}
        {thread.commentCount === null ? null : (
          <span className="inline-flex items-center gap-1">
            <MessageSquare01 aria-hidden="true" className="size-4" />
            {thread.commentCount}
          </span>
        )}
        {thread.lastActivity === null ? null : <time>{thread.lastActivity}</time>}
        <a
          href={sceneHref(
            scene,
            `group/${encodeURIComponent(group.id)}/thread/${encodeURIComponent(thread.id)}`,
          )}
          data-thread-link={thread.id}
          aria-label={`Open thread: ${story === null ? thread.sharedBy.label : story.headline}`}
          className={`font-semibold text-text-link ${FOCUS}`}
        >
          Open thread
        </a>
      </div>
    </li>
  );
}

export function GroupPage({
  scene,
  group,
  writer,
}: {
  scene: SignalScene;
  group: SignalGroup;
  writer: boolean;
}) {
  const stories = new Map(scene.snapshot.feed.stories.map((s) => [s.id, s]));
  return (
    <>
      <Header group={group} writer={writer} />
      {group.threads.length === 0 ? (
        <EmptyState className="py-12">
          <EmptyState.Header>
            <EmptyState.FeaturedIcon />
          </EmptyState.Header>
          <EmptyState.Content>
            <EmptyState.Title>No threads in this group yet</EmptyState.Title>
            <EmptyState.Description>
              {writer
                ? "Share a story from the feed or start a note."
                : "Threads appear here when a writer shares a story or starts a note."}
            </EmptyState.Description>
          </EmptyState.Content>
        </EmptyState>
      ) : (
        <ul
          aria-label="Shared in this group"
          className="mt-4 divide-y divide-border-hairline rounded-ds-lg border border-border-subtle bg-surface-card px-8 py-2 shadow-1"
        >
          {group.threads.map((thread) => {
            const story = thread.storyId === null ? null : (stories.get(thread.storyId) ?? null);
            if (thread.storyId !== null && story === null) {
              throw new Error(`the slice reader let through an unknown story "${thread.storyId}"`);
            }
            return (
              <Item
                key={thread.id}
                scene={scene}
                group={group}
                thread={thread}
                story={story}
                writer={writer}
              />
            );
          })}
        </ul>
      )}
    </>
  );
}
