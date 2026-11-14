// One story as the mock draws it (`.st`): a media object with the publication's monogram, then the
// kind, source and time, the headline, the summary, and the lines the story has. A missing link, time,
// AI line or strength is left out; nothing says "n.a." on a story (component map section 5).
import { useState } from "react";
import { Bookmark, LinkExternal01, MessageSquare01, Share07 } from "@untitledui/icons";
import { Badge } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { cx } from "@/utils/cx";
import { Announcement } from "./parts/Announcement";
import { Avatar } from "./parts/Avatar";
import { AvatarGroup } from "./parts/AvatarGroup";
import { MediaObject } from "./parts/MediaObject";
import { Rating } from "./parts/Rating";
import { Tags } from "./parts/Tags";
import type { SignalStory } from "./slice";

const FOCUS = "outline-focus-ring focus-visible:outline-2";
const LINK = `text-text-link ${FOCUS}`;
/** The predecessor's safe-link test: only an http or https address is drawn as a link. */
const isWebLink = (url: string) => /^https?:\/\//i.test(url);
const ROW = "mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-text-tertiary";

export function StoryCard({ story, writer }: { story: SignalStory; writer: boolean }) {
  const link = story.url !== null && isWebLink(story.url) ? story.url : null;
  const { headline } = story;
  // Save is in memory only: nothing is written; a reload shows the slice's own state again.
  const [saved, setSaved] = useState(story.saved);
  return (
    <article className="py-6">
      <MediaObject tile={story.source.monogram}>
        <div className="mb-1.5 flex flex-wrap items-center gap-2 text-sm text-text-tertiary">
          <Badge size="sm">{story.kindLabel}</Badge>
          <span>{story.source.name}</span>
          {story.time === null ? null : <span>{story.time}</span>}
        </div>
        <h3 className="text-lg font-medium text-text-primary">
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
        </h3>
        {story.summary === null ? null : (
          <p className="mt-0.5 max-w-[72ch] text-text-secondary">{story.summary}</p>
        )}
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
          {writer ? (
            // Wired by the thread and share tasks (8 and 9); until then these act on nothing.
            <>
              <Button
                size="sm"
                color="tertiary"
                iconLeading={MessageSquare01}
                aria-label={`${story.commentCount === null ? "Comment" : `Comment ${story.commentCount}`}: ${headline}`}
              >
                Comment
                {story.commentCount === null ? null : (
                  <Badge size="sm" className="ml-1">
                    {story.commentCount}
                  </Badge>
                )}
              </Button>
              <Button
                size="sm"
                color="tertiary"
                iconLeading={Share07}
                aria-label={`Share to group: ${headline}`}
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
    </article>
  );
}
