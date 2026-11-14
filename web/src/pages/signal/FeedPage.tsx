// A feed page: its view title row, then the stories of the view on one card with hairlines
// between them. The header and the list are separate so the shell can later lay them out full bleed.
import type { SignalStory } from "./slice";
import { StoryCard } from "./StoryCard";

function FeedHeader({ title }: { title: string }) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <h2 className="text-xl font-semibold text-text-primary">{title}</h2>
    </div>
  );
}

/** The stories in the order given (the ids a view lists); no story means nothing is drawn yet. */
function StoryList({ stories, writer }: { stories: SignalStory[]; writer: boolean }) {
  if (stories.length === 0) return null;
  return (
    <div className="mt-4 divide-y divide-border-hairline rounded-ds-lg border border-border-subtle bg-surface-card px-8 py-2 shadow-1">
      {stories.map((story) => (
        <StoryCard key={story.id} story={story} writer={writer} />
      ))}
    </div>
  );
}

export function FeedPage({
  title,
  stories,
  writer,
}: {
  title: string;
  stories: SignalStory[];
  writer: boolean;
}) {
  return (
    <>
      <FeedHeader title={title} />
      <StoryList stories={stories} writer={writer} />
    </>
  );
}
