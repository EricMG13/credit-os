// One story as the mock draws it (`.st`): a media object with the publication's monogram, then the
// kind, source and time, the headline, the summary, and the lines the story has. A missing link, time,
// AI line or strength is left out; nothing says "n.a." on a story (component map section 5).
import { useRef, useState } from "react";
import { Bookmark, LinkExternal01, MessageSquare01, Share07 } from "@untitledui/icons";
import { Badge } from "@/components/base/badges/badges";
import { Button, styles as buttonStyles } from "@/components/base/buttons/button";
import { cx } from "@/utils/cx";
import { Announcement } from "./parts/Announcement";
import { Avatar } from "./parts/Avatar";
import { AvatarGroup } from "./parts/AvatarGroup";
import { MediaObject } from "./parts/MediaObject";
import { BadgeGroup } from "./parts/BadgeGroup";
import { Rating } from "./parts/Rating";
import { StageProgress } from "./parts/StageProgress";
import { Tags } from "./parts/Tags";
import { sceneHref } from "./SignalFrame";
import { ShareDialog } from "./ShareDialog";
import type { SignalScene, SignalStory } from "./slice";

const FOCUS = "outline-focus-ring focus-visible:outline-2";
const LINK = `text-text-link ${FOCUS}`;
/** The predecessor's safe-link test: only an http or https address is drawn as a link. */
export const isWebLink = (url: string) => /^https?:\/\//i.test(url);
const ROW = "mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-text-tertiary";

/**
 * Focus goes to the opener at once and again two frames later if it has fallen to the page: the dialog
 * library restores focus a frame late, and in a browser that restore can leave focus on the body.
 */
function focusOpener(card: HTMLElement | null, label: string) {
  const opener = () =>
    Array.from(card?.querySelectorAll("button") ?? []).find(
      (b) => b.getAttribute("aria-label") === label,
    );
  opener()?.focus();
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (document.activeElement === null || document.activeElement === document.body) {
        opener()?.focus();
      }
    });
  });
}

/** `inGroup`: the card sits in a group view, where "Open thread" is the way in, so a writer's Comment and Share to group are left out. */
type Props = { story: SignalStory; scene: SignalScene; writer: boolean } & (
  | { inGroup: true }
  /** `onShared`: Share was pressed with a group chosen; the page says so (nothing is written). */
  | { inGroup?: false; onShared: () => void }
);

export function StoryCard(props: Props) {
  const { story, scene, writer } = props;
  const inGroup = props.inGroup === true;
  const onShared = props.inGroup === true ? null : props.onShared;
  const link = story.url !== null && isWebLink(story.url) ? story.url : null;
  const { headline } = story;
  // Save is in memory only: nothing is written; a reload shows the slice's own state again.
  const [saved, setSaved] = useState(story.saved);
  // The share dialog opens from Share to group, or from Comment on a story with no thread yet; focus
  // goes back to whichever control opened it.
  const [sharing, setSharing] = useState(false);
  const opener = useRef<"share" | "comment">("share");
  const card = useRef<HTMLElement>(null);
  const share = (from: "share" | "comment") => {
    opener.current = from;
    setSharing(true);
  };
  const commentLabel = `${story.commentCount === null ? "Comment" : `Comment ${story.commentCount}`}: ${headline}`;
  const shareLabel = `Share to group: ${headline}`;
  const commentBody = (
    <span className="inline-flex items-center gap-1 whitespace-nowrap">
      Comment
      {story.commentCount === null ? null : <Badge size="sm">{story.commentCount}</Badge>}
    </span>
  );
  return (
    <article ref={card} className="py-6">
      <MediaObject tile={story.source.monogram}>
        <div className="mb-1.5 flex flex-wrap items-center gap-2 text-sm text-text-tertiary">
          <Badge size="sm">{story.kindLabel}</Badge>
          <span>{story.source.name}</span>
          {story.time === null ? null : <span>{story.time}</span>}
        </div>
        <h2 tabIndex={-1} className="text-lg font-medium text-text-primary">
          {link === null ? (
            headline
          ) : (
            <a
              href={link}
              target="_blank"
              rel="noopener noreferrer"
              className={`text-text-primary hover:underline ${FOCUS}`}
            >
              {headline}
            </a>
          )}
        </h2>
        {story.summary === null ? null : (
          <p className="mt-0.5 max-w-[72ch] text-text-secondary">{story.summary}</p>
        )}
        {story.ratingMoves.length === 0 ? null : (
          <div className={ROW}>
            {story.ratingMoves.map((move, index) => (
              <BadgeGroup key={index} {...move} />
            ))}
          </div>
        )}
        {story.stage === null ? null : <StageProgress stage={story.stage} />}
        {story.ai === null ? null : (
          <div className={ROW}>
            <Announcement>{story.ai.line}</Announcement>
          </div>
        )}
        {story.strength === null && story.alsoIn === null ? null : (
          <div className={ROW}>
            {story.strength === null ? null : (
              <Rating marks={story.strength.marks} word={story.strength.word} />
            )}
            {story.alsoIn === null ? null : (
              <>
                <AvatarGroup monograms={story.alsoIn.monograms} more={story.alsoIn.more} />
                <span>{story.alsoIn.label}</span>
              </>
            )}
          </div>
        )}
        {story.sharedBy === null ? null : (
          <div className={ROW}>
            <Avatar size="xs" initials={story.sharedBy.initials} />
            <span>{story.sharedBy.label}</span>
          </div>
        )}
        {story.tags.length === 0 ? null : (
          <div className="mt-3">
            <Tags tags={story.tags} />
          </div>
        )}
        <div className="mt-3 -ml-3.5 flex flex-wrap items-center gap-1">
          <Button
            size="sm"
            color="tertiary"
            aria-pressed={saved}
            aria-label={`${saved ? "Saved" : "Save"}: ${headline}`}
            className={cx(saved && "text-text-link")}
            iconLeading={<Bookmark data-icon className={cx(saved && "fill-current")} />}
            onPress={() => {
              setSaved(!saved);
            }}
          >
            {saved ? "Saved" : "Save"}
          </Button>
          {writer && !inGroup ? (
            <>
              {story.threadRef === null ? (
                <Button
                  size="sm"
                  color="tertiary"
                  iconLeading={MessageSquare01}
                  aria-label={commentLabel}
                  onPress={() => {
                    share("comment");
                  }}
                >
                  {commentBody}
                </Button>
              ) : (
                <a
                  href={sceneHref(
                    scene,
                    `group/${encodeURIComponent(story.threadRef.groupId)}/thread/${encodeURIComponent(story.threadRef.threadId)}`,
                  )}
                  aria-label={commentLabel}
                  className={cx(
                    buttonStyles.common.root,
                    buttonStyles.sizes.sm.root,
                    buttonStyles.colors.tertiary.root,
                  )}
                >
                  <MessageSquare01 data-icon="leading" aria-hidden="true" />
                  {commentBody}
                </a>
              )}
              <Button
                size="sm"
                color="tertiary"
                iconLeading={Share07}
                aria-label={shareLabel}
                onPress={() => {
                  share("share");
                }}
              >
                Share to group
              </Button>
            </>
          ) : null}
          {link === null ? null : (
            <a
              href={link}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Open source: ${headline} (opens in a new tab)`}
              className={cx("ml-3.5 inline-flex items-center gap-1 text-sm font-semibold", LINK)}
            >
              Open source
              <LinkExternal01 aria-hidden="true" className="size-4" />
            </a>
          )}
        </div>
      </MediaObject>
      {writer && onShared !== null ? (
        <ShareDialog
          open={sharing}
          headline={headline}
          groups={scene.snapshot.groups.map((g) => ({ id: g.id, name: g.name }))}
          onShare={() => {
            setSharing(false);
            onShared();
          }}
          onCancel={() => {
            setSharing(false);
          }}
          onGone={() => {
            focusOpener(card.current, opener.current === "share" ? shareLabel : commentLabel);
          }}
        />
      ) : null}
    </article>
  );
}
