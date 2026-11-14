// A feed page: its view title row, then the entries of the view on one card with hairlines between
// them. An entry is a story or a digest card. The header and the list are separate so the shell can
// later lay them out full bleed.
import { DigestCard } from "./DigestCard";
import type { SignalDigestCard, SignalStory } from "./slice";
import { StoryCard } from "./StoryCard";

export type FeedEntry =
  | { kind: "story"; story: SignalStory }
  | { kind: "digest"; digest: SignalDigestCard; href: string };

function FeedHeader({ title }: { title: string }) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <h2 className="text-xl font-semibold text-text-primary">{title}</h2>
    </div>
  );
}

/** The entries in the order given (the ids a view lists); none means nothing is drawn yet. */
function EntryList({ entries, writer }: { entries: FeedEntry[]; writer: boolean }) {
  if (entries.length === 0) return null;
  return (
    <div className="mt-4 divide-y divide-border-hairline rounded-ds-lg border border-border-subtle bg-surface-card px-8 py-2 shadow-1">
      {entries.map((entry) =>
        entry.kind === "story" ? (
          <StoryCard key={entry.story.id} story={entry.story} writer={writer} />
        ) : (
          <DigestCard key={entry.digest.id} digest={entry.digest} href={entry.href} />
        ),
      )}
    </div>
  );
}

export function FeedPage({
  title,
  entries,
  writer,
}: {
  title: string;
  entries: FeedEntry[];
  writer: boolean;
}) {
  return (
    <>
      <FeedHeader title={title} />
      <EntryList entries={entries} writer={writer} />
    </>
  );
}
