// A feed page: its view title row (title, freshness, Top or Latest), the kind tabs and search, the
// pill for new stories, then the entries on one card with hairlines between them, then Show older.
// An entry is a story or a digest card. Order, filter, search, the pill and Show older all act on
// in-memory state over the entries the slice supplied; nothing is fetched or stored.
import { useEffect, useRef, useState, type Ref } from "react";
import { Star01 } from "@untitledui/icons";
import { Alert } from "@/components/alert/Alert";
import { Button } from "@/components/base/buttons/button";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { DigestCard } from "./DigestCard";
import { FeedControls, OrderToggle, type FeedKind, type FeedOrder } from "./FeedControls";
import { FeedAlert, FeedEmpty, FeedSkeleton, type EmptyContext } from "./FeedStates";
import { FreshnessBadge } from "./parts/FreshnessBadge";
import { PageTitle } from "./parts/PageTitle";
import { Pill } from "./parts/Pill";
import { Tags } from "./parts/Tags";
import type { SignalDigestCard, SignalFreshness, SignalScene, SignalStory } from "./slice";
import { StoryCard } from "./StoryCard";
import { useSignalAnnounce } from "./viewer";

const NOT_SHARED = "Sample data: the story was not shared.";

export type FeedEntry =
  | { kind: "story"; story: SignalStory }
  | { kind: "digest"; digest: SignalDigestCard; href: string };

/** A view's entries as the slice orders them; `waiting` and `older` are the ones not yet drawn. */
export type FeedEntries = {
  top: FeedEntry[];
  latest: FeedEntry[];
  waiting: { label: string; entries: FeedEntry[] } | null;
  older: FeedEntry[];
};

/** A topic view's own header parts: the follow state and the keywords it follows. */
export type FeedTopic = { on: boolean; onToggle: () => void; keywords: string[] };

function FeedHeader({
  title,
  titleRef,
  freshness,
  order,
  onOrder,
  topic,
}: {
  title: string;
  titleRef: Ref<HTMLHeadingElement>;
  freshness: SignalFreshness;
  order: FeedOrder;
  /** Absent where the view has one order only (Latest and Saved draw no switch). */
  onOrder: ((order: FeedOrder) => void) | null;
  topic: FeedTopic | null;
}) {
  return (
    <>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <PageTitle titleRef={titleRef}>{title}</PageTitle>
        {topic === null ? null : (
          <Button
            color={topic.on ? "secondary" : "tertiary"}
            size="sm"
            iconLeading={<Star01 data-icon className={topic.on ? "fill-current" : undefined} />}
            aria-pressed={topic.on}
            onPress={topic.onToggle}
          >
            {topic.on ? "Following" : "Follow"}
          </Button>
        )}
        <FreshnessBadge freshness={freshness} />
        {onOrder === null ? null : (
          <div className="ml-auto">
            <OrderToggle order={order} onOrder={onOrder} />
          </div>
        )}
      </div>
      {topic === null || topic.keywords.length === 0 ? null : (
        <div className="mt-3">
          <Tags tags={topic.keywords} label="Topic keywords" />
        </div>
      )}
    </>
  );
}

/** Stories of the chosen kind whose headline, summary, source name or tag holds the query; a digest card is under All with no query only. */
function visible(entries: FeedEntry[], kind: FeedKind, query: string): FeedEntry[] {
  const needle = query.toLowerCase();
  return entries.filter((entry) => {
    if (entry.kind === "digest") return kind === "all" && needle === "";
    const { story } = entry;
    if (kind !== "all" && story.kind !== kind) return false;
    if (needle === "") return true;
    return [story.headline, story.summary ?? "", story.source.name, ...story.tags].some((text) =>
      text.toLowerCase().includes(needle),
    );
  });
}

function NoMatch({ title, hint }: { title: string; hint: string }) {
  return (
    <EmptyState className="mt-4 py-12">
      <EmptyState.Header>
        <EmptyState.FeaturedIcon />
      </EmptyState.Header>
      <EmptyState.Content>
        <EmptyState.Title>{title}</EmptyState.Title>
        <EmptyState.Description>{hint}</EmptyState.Description>
      </EmptyState.Content>
    </EmptyState>
  );
}

/** The entries in the order given; none means nothing is drawn yet. */
function EntryList({
  entries,
  scene,
  writer,
  onShared,
  listRef,
}: {
  entries: FeedEntry[];
  scene: SignalScene;
  writer: boolean;
  onShared: () => void;
  listRef: Ref<HTMLDivElement>;
}) {
  if (entries.length === 0) return null;
  return (
    <div
      ref={listRef}
      className="mt-4 divide-y divide-border-hairline rounded-ds-lg border border-border-subtle bg-surface-card px-8 py-2 shadow-1"
    >
      {entries.map((entry) =>
        entry.kind === "story" ? (
          <StoryCard
            key={entry.story.id}
            story={entry.story}
            scene={scene}
            writer={writer}
            onShared={onShared}
          />
        ) : (
          <DigestCard key={entry.digest.id} digest={entry.digest} href={entry.href} />
        ),
      )}
    </div>
  );
}

export function FeedPage({
  scene,
  title: heading,
  freshness,
  entries,
  startOn,
  switchable,
  writer,
  loading,
  error,
  empty,
  topic,
}: {
  scene: SignalScene;
  title: string;
  freshness: SignalFreshness;
  entries: FeedEntries;
  /** The order the view starts on; with `switchable` false it is the only order. */
  startOn: FeedOrder;
  switchable: boolean;
  writer: boolean;
  /** The feed is still loading: the skeleton stands in for the list. */
  loading: boolean;
  error: "unreachable" | "request" | "unreadable" | null;
  empty: EmptyContext;
  /** Set on a topic's view only. */
  topic: FeedTopic | null;
}) {
  const [order, setOrder] = useState<FeedOrder>(startOn);
  const [kind, setKind] = useState<FeedKind>("all");
  const [query, setQuery] = useState("");
  const [revealed, setRevealed] = useState(false);
  const [olderShown, setOlderShown] = useState(false);
  // Share to group writes nothing: this sentence is the in-memory stand-in for the service's reply.
  // The frame's one status region announces it (each call is new content there); the visible alert
  // below is not a second live region.
  const [shared, setShared] = useState(0);
  const announce = useSignalAnnounce();
  // After the list grows, focus goes to the first story the change brought in (its headline); when
  // the kind or search hides every one of them, it goes to the page title instead.
  const list = useRef<HTMLDivElement>(null);
  const title = useRef<HTMLHeadingElement>(null);
  const focusAt = useRef<number | "title" | null>(null);
  useEffect(() => {
    const at = focusAt.current;
    focusAt.current = null;
    if (at === null) return;
    if (at === "title") title.current?.focus();
    else list.current?.querySelectorAll("article")[at]?.querySelector("h2")?.focus();
  }, [revealed, olderShown]);
  const { waiting, older } = entries;
  const needle = query.trim();
  const drawn = [
    ...(revealed && waiting !== null ? waiting.entries : []),
    ...entries[order],
    ...(olderShown ? older : []),
  ];
  const shown = visible(drawn, kind, needle);
  return (
    <>
      <FeedHeader
        title={heading}
        titleRef={title}
        topic={topic}
        freshness={freshness}
        order={order}
        onOrder={switchable ? setOrder : null}
      />
      <FeedControls kind={kind} onKind={setKind} query={query} onQuery={setQuery} />
      {loading || waiting === null || revealed ? null : (
        <div className="mt-4 flex justify-center">
          <Pill
            label={waiting.label}
            action="Show"
            onAction={() => {
              focusAt.current = visible(waiting.entries, kind, needle).length > 0 ? 0 : "title";
              setRevealed(true);
            }}
          />
        </div>
      )}
      {error === null ? null : <FeedAlert error={error} />}
      {shared > 0 ? (
        <div className="mt-4">
          <Alert live={false} tone="success" title={NOT_SHARED} />
        </div>
      ) : null}
      {loading ? (
        <FeedSkeleton />
      ) : shown.length > 0 ? (
        <EntryList
          entries={shown}
          scene={scene}
          writer={writer}
          onShared={() => {
            setShared(shared + 1);
            announce(NOT_SHARED);
          }}
          listRef={list}
        />
      ) : needle !== "" ? (
        <NoMatch
          title={`No story matches ${needle}`}
          hint="Check the spelling or clear the search."
        />
      ) : kind !== "all" ? (
        <NoMatch title="No stories of this kind here" hint="Choose All to see every kind." />
      ) : (
        <FeedEmpty context={empty} />
      )}
      {loading || older.length === 0 || olderShown ? null : (
        <div className="mt-4 flex justify-center">
          <Button
            color="secondary"
            size="sm"
            onPress={() => {
              focusAt.current = visible(older, kind, needle).length > 0 ? shown.length : "title";
              setOlderShown(true);
            }}
          >
            Show older
          </Button>
        </div>
      )}
    </>
  );
}
