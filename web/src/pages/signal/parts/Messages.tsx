// The conversation (I7, structure from sources/live-pages.md, look from mock/signal.css `.m`, `.bub`,
// `.rx`, `.cmp`): an ordered list of comments with one level of replies, and the composer. Comment
// text is plain text (never HTML, no link detection). Nothing here keeps state of its own except the
// composer's text: the page owns what was posted and which reactions were toggled.
import { useState, type RefObject, type SyntheticEvent } from "react";
import { Button } from "@/components/base/buttons/button";
import type { SignalComment } from "../slice";
import { cx } from "@/utils/cx";
import { Avatar } from "./Avatar";
import { TextArea } from "./TextArea";

/** Ruling 19 fixes the set; each is drawn on every comment that is not removed. */
const REACTION_WORDS = ["Agree", "Disagree", "Seen"] as const;
type ReactionWord = (typeof REACTION_WORDS)[number];

const FOCUS = "outline-focus-ring focus-visible:outline-2";

type ListProps = {
  comments: SignalComment[];
  /** A writer on an open thread can reply; otherwise null and no Reply is drawn. */
  onReply: ((comment: SignalComment) => void) | null;
  isPressed: (comment: SignalComment, word: ReactionWord) => boolean;
  onToggle: (comment: SignalComment, word: ReactionWord) => void;
};

/** Own comments are labelled "You" whatever name they carry. */
const authorOf = (comment: SignalComment) => (comment.own ? "You" : comment.author.name);

function Reactions({
  comment,
  isPressed,
  onToggle,
}: { comment: SignalComment } & Pick<ListProps, "isPressed" | "onToggle">) {
  const author = authorOf(comment);
  return (
    <ul aria-label={`Reactions to the comment by ${author}`} className="flex gap-1">
      {REACTION_WORDS.map((word) => {
        // A word the slice does not hold has no count; one it holds shows the delivered string.
        const count = comment.reactions.find((r) => r.word === word)?.count ?? null;
        const on = isPressed(comment, word);
        return (
          <li key={word}>
            <button
              type="button"
              aria-pressed={on}
              aria-label={`${word}${count === null ? "" : `, ${count}`}: comment by ${author}`}
              onClick={() => {
                onToggle(comment, word);
              }}
              className={cx(
                "h-6 rounded-ds-full px-2 text-sm font-medium ring-1 ring-border-hairline ring-inset",
                FOCUS,
                on
                  ? "bg-surface-selected text-text-link"
                  : "bg-surface-subtle text-text-secondary hover:bg-surface-card",
              )}
            >
              {count === null ? word : `${word} ${count}`}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function Message({
  comment,
  quote,
  isReply,
  onReply,
  isPressed,
  onToggle,
}: {
  comment: SignalComment;
  /** What a reply quotes: its parent's text (none when the parent was removed). */
  quote: string | null;
  isReply: boolean;
} & Omit<ListProps, "comments">) {
  const author = authorOf(comment);
  const when = [comment.time, comment.edited ? "edited" : null]
    .filter((s) => s !== null)
    .join(", ");
  return (
    <li className={cx("flex items-start gap-3", comment.own ? "self-end pl-10" : "pr-10")}>
      {comment.own ? null : <Avatar size="sm" initials={comment.author.initials} />}
      <article className="flex min-w-0 flex-1 flex-col gap-1.5">
        <header className="flex items-center gap-2">
          <cite className="flex-1 text-sm font-medium text-text-secondary not-italic">
            {author}
          </cite>
          {when === "" ? null : <span className="text-xs text-text-tertiary">{when}</span>}
        </header>
        {comment.removed ? (
          <p className="rounded-ds-sm border border-border-hairline bg-surface-card px-3 py-2 text-text-tertiary">
            This comment was removed by its author.
          </p>
        ) : (
          <div
            className={cx(
              "rounded-ds-sm border border-border-hairline px-3 py-2 whitespace-pre-wrap break-words text-text-primary",
              comment.own ? "bg-surface-card" : "bg-surface-subtle",
            )}
          >
            {quote === null ? null : (
              <blockquote className="mb-1.5 rounded-ds-sm border border-border-hairline border-l-[3px] border-l-action bg-surface-card px-3 py-2 text-sm text-text-tertiary">
                {quote}
              </blockquote>
            )}
            {comment.text}
          </div>
        )}
        {comment.removed ? null : (
          <div className="flex items-center justify-between gap-2">
            {onReply === null || isReply ? (
              <span />
            ) : (
              <button
                type="button"
                aria-label={`Reply to ${author}`}
                onClick={() => {
                  onReply(comment);
                }}
                className={cx("rounded-ds-xs text-sm font-semibold text-text-link", FOCUS)}
              >
                Reply
              </button>
            )}
            <Reactions comment={comment} isPressed={isPressed} onToggle={onToggle} />
          </div>
        )}
        {comment.replies.length === 0 ? null : (
          <ol aria-label={`Replies to ${author}`} className="mt-2 flex flex-col gap-4 pl-8">
            {comment.replies.map((reply) => (
              <Message
                key={reply.id}
                comment={reply}
                quote={comment.text}
                isReply
                onReply={onReply}
                isPressed={isPressed}
                onToggle={onToggle}
              />
            ))}
          </ol>
        )}
      </article>
    </li>
  );
}

export function MessageList({ comments, ...rest }: ListProps) {
  return (
    <ol aria-label="Comments" className="flex flex-col gap-4">
      {comments.map((comment) => (
        <Message key={comment.id} comment={comment} quote={null} isReply={false} {...rest} />
      ))}
    </ol>
  );
}

type ComposerProps = {
  /** The viewer's name and initials, as the frame shows them under the box. */
  name: string;
  initials: string | null;
  /** The comment being replied to, or null for a new top-level comment. */
  replyingTo: string | null;
  onCancelReply: () => void;
  /** Gets the text with its ends trimmed; the composer clears itself after. */
  onSend: (text: string) => void;
  boxRef: RefObject<HTMLTextAreaElement | null>;
};

export function Composer({
  name,
  initials,
  replyingTo,
  onCancelReply,
  onSend,
  boxRef,
}: ComposerProps) {
  const [text, setText] = useState("");
  const [empty, setEmpty] = useState(false);
  const submit = (event: SyntheticEvent) => {
    event.preventDefault();
    const sent = text.trim();
    if (sent === "") {
      setEmpty(true);
    } else {
      setEmpty(false);
      setText("");
      onSend(sent);
    }
    // Focus stays in the box after a send and after an empty one.
    boxRef.current?.focus();
  };
  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-2">
      {replyingTo === null ? null : (
        <p className="flex items-center justify-between gap-2 text-sm text-text-secondary">
          <span>Replying to {replyingTo}</span>
          <Button
            size="sm"
            color="link-color"
            onPress={() => {
              onCancelReply();
              boxRef.current?.focus();
            }}
          >
            Cancel
          </Button>
        </p>
      )}
      <div className="rounded-ds-lg border border-border-hairline bg-surface-subtle">
        <TextArea
          aria-label="Write a comment"
          placeholder="Write a comment"
          rows={3}
          value={text}
          onChange={(next) => {
            setText(next);
            setEmpty(false);
          }}
          textAreaRef={boxRef}
          isInvalid={empty}
          hint={empty ? "Write something first." : undefined}
        />
        <div className="flex items-center justify-between gap-3 px-3 py-2 text-xs font-semibold text-text-tertiary">
          <span className="flex items-center gap-1">
            <Avatar size="xs" initials={initials} own />
            {name}
          </span>
          <Button size="sm" color="link-color" type="submit">
            Send
          </Button>
        </div>
      </div>
    </form>
  );
}
