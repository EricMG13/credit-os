// One story as the mock draws it (`.st`): a media object with the publication's monogram, then the
// kind, source and time, the headline, the summary, and the lines the story has. A missing link, time,
// AI line or strength is left out; nothing says "n.a." on a story (component map section 5).
import { useRef, useState } from "react";
import { Bookmark, MessageSquare01, Share07 } from "@untitledui/icons";
import { Badge } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { cx } from "@/utils/cx";
import { Announcement } from "./parts/Announcement";
import { Avatar } from "./parts/Avatar";
import { AvatarGroup } from "./parts/AvatarGroup";
import { focusAgainIfLost } from "./parts/focus";
import { MediaObject } from "./parts/MediaObject";
import { OpenSourceButton } from "./parts/OpenSourceButton";
import { BadgeGroup } from "./parts/BadgeGroup";
import { Rating } from "./parts/Rating";
import { StageProgress } from "./parts/StageProgress";
import { Tags } from "./parts/Tags";
import { sceneHref } from "./SignalFrame";
import { ShareDialog } from "./ShareDialog";
import type { SignalScene, SignalStory } from "./slice";

const FOCUS = "outline-focus-ring focus-visible:outline-2";
/** The predecessor's safe-link test: only an http or https address is drawn as a link. */
export const isWebLink = (url: string) => /^https?:\/\//i.test(url);
const ROW = "mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-text-tertiary";

/** The control that opened the share dialog, found by its label inside the card. */
function openerIn(card: HTMLElement | null, label: string) {
  return Array.from(card?.querySelectorAll("button") ?? []).find(
    (b) => b.getAttribute("aria-label") === label,
  );
}

/** The saved choice by story id, kept above every list so a filter or a page change does not forget it; in memory only. */
export type SignalSave = {
  on: (story: { id: string; saved: boolean }) => boolean;
  toggle: (story: { id: string; saved: boolean }) => void;
};

/** `inGroup`: the card sits in a group view, where "Open thread" is the way in, so a writer's Comment and Share to group are left out. */
type Props = { story: SignalStory; scene: SignalScene; writer: boolean; save: SignalSave } & (
  | { inGroup: true }
  /** `onShared`: Share was pressed with a group chosen; the page says so (nothing is written). */
  | { inGroup?: false; onShared: () => void }
);

type ShareFrom = "share" | "comment";

const commentLabelOf = (story: SignalStory) =>
  `${story.commentCount === null ? "Comment" : `Comment ${story.commentCount}`}: ${story.headline}`;
const shareLabelOf = (story: SignalStory) => `Share to group: ${story.headline}`;

/** The kind, source and time line above the headline. */
function Byline({ story }: { story: SignalStory }) {
  return (
    <div className="mb-1.5 flex flex-wrap items-center gap-2 text-sm text-text-tertiary">
      <Badge size="sm">{story.kindLabel}</Badge>
      <span>{story.source.name}</span>
      {story.time === null ? null : <span>{story.time}</span>}
    </div>
  );
}

/** The headline, a link when the story has a web link, and the summary. */
function HeadlineBlock({ story, link }: { story: SignalStory; link: string | null }) {
  const { headline } = story;
  return (
    <>
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
    </>
  );
}

/** The rating moves, stage, AI line and strength rows; each is left out when the story lacks it. */
function SignalRows({ story }: { story: SignalStory }) {
  return (
    <>
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
    </>
  );
}

/** The shared-by row and the tags. */
function ShareRows({ story }: { story: SignalStory }) {
  return (
    <>
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
    </>
  );
}

/** A writer's Comment (opens the share dialog, or the thread when there is one) and Share to group. */
function WriterActions({
  story,
  scene,
  onShare,
}: {
  story: SignalStory;
  scene: SignalScene;
  onShare: (from: ShareFrom) => void;
}) {
  const commentLabel = commentLabelOf(story);
  const commentBody = (
    <span className="inline-flex items-center gap-1 whitespace-nowrap">
      Comment
      {story.commentCount === null ? null : <Badge size="sm">{story.commentCount}</Badge>}
    </span>
  );
  return (
    <>
      {story.threadRef === null ? (
        <Button
          size="sm"
          color="tertiary"
          iconLeading={MessageSquare01}
          aria-label={commentLabel}
          onPress={() => {
            onShare("comment");
          }}
        >
          {commentBody}
        </Button>
      ) : (
        <Button
          size="sm"
          color="tertiary"
          iconLeading={MessageSquare01}
          href={sceneHref(
            scene,
            `group/${encodeURIComponent(story.threadRef.groupId)}/thread/${encodeURIComponent(story.threadRef.threadId)}`,
          )}
          aria-label={commentLabel}
        >
          {commentBody}
        </Button>
      )}
      <Button
        size="sm"
        color="tertiary"
        iconLeading={Share07}
        aria-label={shareLabelOf(story)}
        onPress={() => {
          onShare("share");
        }}
      >
        Share to group
      </Button>
    </>
  );
}

/** The action row: Save, the writer's Comment and Share, and Open source. */
function Actions({
  story,
  scene,
  link,
  saved,
  save,
  writerActions,
  onShare,
}: {
  story: SignalStory;
  scene: SignalScene;
  link: string | null;
  saved: boolean;
  save: SignalSave;
  writerActions: boolean;
  onShare: (from: ShareFrom) => void;
}) {
  return (
    <div className="mt-3 -ml-3.5 flex flex-wrap items-center gap-1">
      <Button
        size="sm"
        color="tertiary"
        aria-pressed={saved}
        aria-label={`${saved ? "Saved" : "Save"}: ${story.headline}`}
        className={cx(saved && "text-text-link")}
        iconLeading={<Bookmark data-icon className={cx(saved && "fill-current")} />}
        onPress={() => {
          save.toggle(story);
        }}
      >
        {saved ? "Saved" : "Save"}
      </Button>
      {writerActions ? <WriterActions story={story} scene={scene} onShare={onShare} /> : null}
      {link === null ? null : (
        <OpenSourceButton url={link} headline={story.headline} className="ml-3.5" />
      )}
    </div>
  );
}

export function StoryCard(props: Props) {
  const { story, scene, writer, save } = props;
  const inGroup = props.inGroup === true;
  const onShared = props.inGroup === true ? null : props.onShared;
  const link = story.url !== null && isWebLink(story.url) ? story.url : null;
  const { headline } = story;
  // Save is in memory only: nothing is written; a reload shows the slice's own state again.
  const saved = save.on(story);
  // The share dialog opens from Share to group, or from Comment on a story with no thread yet; focus
  // goes back to whichever control opened it.
  const [sharing, setSharing] = useState(false);
  const opener = useRef<ShareFrom>("share");
  const card = useRef<HTMLElement>(null);
  const share = (from: ShareFrom) => {
    opener.current = from;
    setSharing(true);
  };
  return (
    <article ref={card} className="py-6">
      <MediaObject tile={story.source.monogram}>
        <Byline story={story} />
        <HeadlineBlock story={story} link={link} />
        <SignalRows story={story} />
        <ShareRows story={story} />
        <Actions
          story={story}
          scene={scene}
          link={link}
          saved={saved}
          save={save}
          writerActions={writer && !inGroup}
          onShare={share}
        />
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
            const label = opener.current === "share" ? shareLabelOf(story) : commentLabelOf(story);
            focusAgainIfLost(() => openerIn(card.current, label));
          }}
        />
      ) : null}
    </article>
  );
}
