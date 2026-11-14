// The thread panel (mock frames "Thread panel" and "Thread archived"; behaviour list 2.9): the kit's
// slide-out menu, open on the thread route, over the group view. It shows the quoted story or the
// note, the comments, and for a writer on an open thread the composer. Closing goes back to the group
// route and moves focus to that thread's "Open thread" link. Everything here is in memory: posting
// adds the comment to this page's list and a reaction toggle flips its pressed state; no count is
// recomputed (the delivered string stays) and nothing is written.
import { useEffect, useRef, useState } from "react";
import { LinkExternal01 } from "@untitledui/icons";
import { SlideoutMenu } from "@/components/application/slideout-menus/slideout-menu";
import { Badge } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { CloseButton } from "@/components/base/buttons/close-button";
import { cx } from "@/utils/cx";
import { sceneHref } from "./SignalFrame";
import { isWebLink } from "./StoryCard";
import { ArchivedBadge } from "./parts/ArchivedBadge";
import { MediaObject } from "./parts/MediaObject";
import { Composer, MessageList } from "./parts/Messages";
import type { ReactionWord } from "./parts/Messages";
import type { SignalComment, SignalGroup, SignalScene, SignalStory, SignalThread } from "./slice";
import { useSignalViewer } from "./viewer";

const TITLE_ID = "signal-thread-title";
const FOCUS = "outline-focus-ring focus-visible:outline-2";

/** Runs once when the panel's content goes (after any exit animation), so focus never falls to the page. */
function useOnGone(then: () => void) {
  const latest = useRef(then);
  useEffect(() => {
    latest.current = then;
  });
  useEffect(
    () => () => {
      latest.current();
    },
    [],
  );
}

/** The thread's own "Open thread" link in the group view; the page container when there is none. */
function openLinkTarget(threadId: string | null): HTMLElement | null {
  const links = document.querySelectorAll<HTMLElement>("a[data-thread-link]");
  const own = [...links].find((a) => a.dataset["threadLink"] === threadId);
  return own ?? document.getElementById("signal-content");
}

/**
 * Focus goes to the link at once and again two frames later if it has fallen to the page. When the
 * address was loaded directly the dialog library has no opener to restore and, in a browser, its own
 * frame-late restore leaves focus on the body; a click-opened panel is restored to its link by it.
 */
function focusOpenLink(threadId: string | null) {
  openLinkTarget(threadId)?.focus();
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (document.activeElement === null || document.activeElement === document.body) {
        openLinkTarget(threadId)?.focus();
      }
    });
  });
}

function Quoted({ story }: { story: SignalStory }) {
  const link = story.url !== null && isWebLink(story.url) ? story.url : null;
  return (
    <article>
      <MediaObject tile={story.source.monogram}>
        <div className="mb-1.5 flex flex-wrap items-center gap-2 text-sm text-text-tertiary">
          <Badge size="sm">{story.kindLabel}</Badge>
          <span>{story.source.name}</span>
          {story.time === null ? null : <span>{story.time}</span>}
        </div>
        <h3 className="text-lg font-medium text-text-primary">
          {link === null ? (
            story.headline
          ) : (
            <a
              href={link}
              target="_blank"
              rel="noopener noreferrer"
              className={cx("hover:underline", FOCUS)}
            >
              {story.headline}
            </a>
          )}
        </h3>
        {link === null ? null : (
          <Button
            size="sm"
            color="link-color"
            iconTrailing={LinkExternal01}
            href={link}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Open source: ${story.headline} (opens in a new tab)`}
            className="mt-2"
          >
            Open source
          </Button>
        )}
      </MediaObject>
    </article>
  );
}

type Added = { parentId: string | null; comment: SignalComment };

/** The thread's comments with what the viewer posted in this visit: a reply under its parent, the rest last. */
function withAdded(comments: SignalComment[], added: Added[]): SignalComment[] {
  const top = [...comments, ...added.filter((a) => a.parentId === null).map((a) => a.comment)];
  return top.map((c) => ({
    ...c,
    replies: [...c.replies, ...added.filter((a) => a.parentId === c.id).map((a) => a.comment)],
  }));
}

/** An id no comment of the thread holds yet, for a comment posted in memory. */
function freshId(thread: SignalThread, added: Added[]): string {
  const held = new Set([
    ...thread.comments.flatMap((c) => [c.id, ...c.replies.map((r) => r.id)]),
    ...added.map((a) => a.comment.id),
  ]);
  let n = added.length + 1;
  while (held.has(`posted-${String(n)}`)) n += 1;
  return `posted-${String(n)}`;
}

const NOTE = "text-sm text-text-tertiary";
const pressKey = (comment: SignalComment, word: ReactionWord) => JSON.stringify([comment.id, word]);

/** The thread's top, comments and footer; its state (what was posted, which reactions flipped) lives here. */
function Conversation({
  thread,
  story,
  writer,
}: {
  thread: SignalThread;
  story: SignalStory | null;
  writer: boolean;
}) {
  const viewer = useSignalViewer();
  const box = useRef<HTMLTextAreaElement>(null);
  const [added, setAdded] = useState<Added[]>([]);
  const [replyTo, setReplyTo] = useState<SignalComment | null>(null);
  const [flipped, setFlipped] = useState<ReadonlySet<string>>(new Set());
  const [said, setSaid] = useState("");
  const comments = withAdded(thread.comments, added);
  const named = viewer.name !== null && viewer.initials !== null;
  const canWrite = writer && !thread.archived;
  const send = (text: string) => {
    if (viewer.name === null || viewer.initials === null) {
      throw new Error("the composer was drawn with no viewer name");
    }
    const comment: SignalComment = {
      id: freshId(thread, added),
      author: { initials: viewer.initials, name: viewer.name },
      own: true,
      time: null,
      text,
      edited: false,
      removed: false,
      reactions: [],
      replies: [],
    };
    setAdded([...added, { parentId: replyTo?.id ?? null, comment }]);
    setReplyTo(null);
    setSaid(replyTo === null ? "Comment posted" : `Reply to ${replyTo.author.name} posted`);
  };
  let footer;
  if (thread.archived) {
    footer = <p className={NOTE}>This thread is archived. It can be read but not added to.</p>;
  } else if (!writer) {
    footer = <p className={NOTE}>Readers see this thread but not the reply box.</p>;
  } else if (viewer.name === null || viewer.initials === null) {
    footer = <p className={NOTE}>Set your name to write a comment.</p>;
  } else {
    footer = (
      <Composer
        name={viewer.name}
        initials={viewer.initials}
        replyingTo={replyTo === null ? null : replyTo.author.name}
        onCancelReply={() => {
          setReplyTo(null);
        }}
        onSend={send}
        boxRef={box}
      />
    );
  }
  return (
    <>
      <SlideoutMenu.Content>
        {thread.archivedLine === null ? null : (
          <div className="self-start">
            <ArchivedBadge>{thread.archivedLine}</ArchivedBadge>
          </div>
        )}
        {story === null ? null : <Quoted story={story} />}
        {thread.note === null ? null : (
          <p className="rounded-ds-sm border border-border-hairline bg-surface-subtle px-3 py-2 whitespace-pre-wrap break-words text-text-primary">
            {thread.note}
          </p>
        )}
        {comments.length === 0 ? (
          <p className={NOTE}>No comments yet</p>
        ) : (
          <MessageList
            comments={comments}
            onReply={
              canWrite && named
                ? (comment) => {
                    setReplyTo(comment);
                    box.current?.focus();
                  }
                : null
            }
            isPressed={(comment, word) =>
              (comment.reactions.find((r) => r.word === word)?.mine ?? false) !==
              flipped.has(pressKey(comment, word))
            }
            onToggle={(comment, word) => {
              const next = new Set(flipped);
              const key = pressKey(comment, word);
              if (!next.delete(key)) next.add(key);
              setFlipped(next);
            }}
          />
        )}
        <div role="status" className="sr-only">
          {said}
        </div>
      </SlideoutMenu.Content>
      <SlideoutMenu.Footer>{footer}</SlideoutMenu.Footer>
    </>
  );
}

export function ThreadPanel({
  scene,
  group,
  thread,
  writer,
}: {
  scene: SignalScene;
  group: SignalGroup;
  /** Null when the address names no thread of this group. */
  thread: SignalThread | null;
  writer: boolean;
}) {
  useOnGone(() => {
    focusOpenLink(thread === null ? null : thread.id);
  });
  const close = () => {
    window.location.hash = sceneHref(scene, `group/${encodeURIComponent(group.id)}`);
  };
  const story =
    thread === null || thread.storyId === null
      ? null
      : (scene.snapshot.feed.stories.find((s) => s.id === thread.storyId) ?? null);
  if (thread !== null && thread.storyId !== null && story === null) {
    throw new Error(`the slice reader let through an unknown story "${thread.storyId}"`);
  }
  return (
    <SlideoutMenu
      isOpen
      isDismissable
      aria-labelledby={TITLE_ID}
      // Ruling 20: the feed stays readable, so the kit's overlay token is drawn lighter.
      className="bg-overlay/30"
      onOpenChange={(open) => {
        if (!open) close();
      }}
    >
      <header className="relative w-full px-6 pt-6">
        <h2 id={TITLE_ID} className="pr-10 text-lg font-semibold text-text-primary">
          {thread === null ? "Thread not found" : thread.title}
        </h2>
        <p className="text-sm text-text-tertiary">
          {thread === null ? "This thread does not exist or is not open to you." : thread.subline}
        </p>
        <CloseButton label="Close thread" className="absolute top-3 right-3" />
      </header>
      {thread === null ? null : (
        <Conversation
          key={JSON.stringify([thread.groupId, thread.id])}
          thread={thread}
          story={story}
          writer={writer}
        />
      )}
    </SlideoutMenu>
  );
}
