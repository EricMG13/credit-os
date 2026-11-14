// One Signal address: picks the scene, then what the frame holds. Pages later tasks build replace
// the "Not built yet" empty state.
import { useState, type ReactNode } from "react";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { useSource } from "../source";
import { SignalFrame, sceneHref, type SignalCurrent, type SignalFollow } from "./SignalFrame";
import { DigestPage } from "./DigestPage";
import { GroupPage } from "./GroupPage";
import { ThreadPanel } from "./ThreadPanel";
import { FeedPage, type FeedEntries, type FeedEntry } from "./FeedPage";
import type { EmptyContext } from "./FeedStates";
import { PageTitle } from "./parts/PageTitle";
import { readSlice, type SignalFeedView, type SignalScene } from "./slice";

export type SignalPageKind = "feed" | "topic" | "group" | "thread" | "digest" | "settings";

const VIEWS = { "for-you": "For you", latest: "Latest", saved: "Saved" } as const;

/** An empty state; `page` makes its title the page's h1 (the kit's title stops at h2), else it is an h2 under one. */
function Empty({
  title,
  page = false,
  children,
}: {
  title: string;
  page?: boolean;
  children?: ReactNode;
}) {
  return (
    <EmptyState className="py-12">
      <EmptyState.Header>
        <EmptyState.FeaturedIcon />
      </EmptyState.Header>
      <EmptyState.Content>
        {page ? <PageTitle>{title}</PageTitle> : <EmptyState.Title>{title}</EmptyState.Title>}
      </EmptyState.Content>
      {children}
    </EmptyState>
  );
}

/** The entries a view lists, in its order; an id the feed lacks cannot reach here (the reader refuses it). */
function ordered(scene: SignalScene, ids: string[]): FeedEntry[] {
  const { stories, digests } = scene.snapshot.feed;
  const byId = new Map<string, FeedEntry>([
    ...stories.map((story): [string, FeedEntry] => [story.id, { kind: "story", story }]),
    ...digests.map((digest): [string, FeedEntry] => [
      digest.id,
      {
        kind: "digest",
        digest,
        href: sceneHref(scene, `digest/${encodeURIComponent(digest.digestId)}`),
      },
    ]),
  ]);
  return ids.map((id) => {
    const entry = byId.get(id);
    if (entry === undefined)
      throw new Error(`the slice reader let through an unknown entry "${id}"`);
    return entry;
  });
}

/** All the entries a view supplies: both orders, the waiting ones and the older ones. */
function entriesOf(scene: SignalScene, view: SignalFeedView): FeedEntries {
  return {
    top: ordered(scene, view.top),
    latest: ordered(scene, view.latest),
    waiting:
      view.waiting === null
        ? null
        : { label: view.waiting.label, entries: ordered(scene, view.waiting.ids) },
    older: ordered(scene, view.older),
  };
}

/** The reader gives every channel topic an order; a missing one is a wiring fault, so it is loud. */
function topicView(scene: SignalScene, id: string): SignalFeedView {
  const { topics } = scene.snapshot.feed;
  const order = Object.hasOwn(topics, id) ? topics[id] : undefined;
  if (order === undefined)
    throw new Error(`the slice reader let through topic "${id}" with no order`);
  return order;
}

/** The route pattern guarantees these segments; a missing one is a wiring fault, so it is loud. */
function param(params: Record<string, string>, name: string): string {
  const value = params[name];
  if (value === undefined) throw new Error(`the route gave no "${name}" segment`);
  return value;
}

/** What a feed view needs to say why it is empty, with the follow state it shares with the channel list. */
function emptyContext(
  scene: SignalScene,
  view: EmptyContext["view"],
  follow: SignalFollow,
  writer: boolean,
): EmptyContext {
  const { channels, feed } = scene.snapshot;
  return {
    view,
    approved: feed.sources.approved,
    propose: writer ? sceneHref(scene, "settings/sources") : null,
    noneFollowed: !channels.topics.some((t) => t.followed),
    topics: channels.topics.map((t) => ({ id: t.id, name: t.name, on: follow.on(t) })),
    onFollow: (id) => {
      const topic = channels.topics.find((t) => t.id === id);
      if (topic === undefined) throw new Error(`the empty state named an unknown topic "${id}"`);
      follow.toggle(topic);
    },
  };
}

function Body({
  scene,
  kind,
  params,
  follow,
}: {
  scene: SignalScene;
  kind: SignalPageKind;
  params: Record<string, string>;
  follow: SignalFollow;
}): {
  current: SignalCurrent;
  body: ReactNode;
} {
  const back = (
    <EmptyState.Footer>
      <a className="text-sm font-semibold text-text-link" href={sceneHref(scene, "feed/for-you")}>
        Back to For you
      </a>
    </EmptyState.Footer>
  );
  const writer = scene.snapshot.viewer.role === "writer";
  switch (kind) {
    case "feed": {
      const view = Object.keys(VIEWS).find((id) => id === params["view"]);
      if (view === undefined) {
        return {
          current: { kind: "none" },
          body: (
            <Empty page title="No such view">
              {back}
            </Empty>
          ),
        };
      }
      const id = view as keyof typeof VIEWS;
      return {
        current: { kind: "view", id },
        body: (
          <FeedPage
            scene={scene}
            key={`${scene.id}/feed/${id}`}
            title={VIEWS[id]}
            freshness={scene.snapshot.feed.freshness}
            entries={entriesOf(scene, scene.snapshot.feed.views[id])}
            startOn={id === "for-you" ? "top" : "latest"}
            switchable={id === "for-you"}
            writer={writer}
            loading={scene.snapshot.feed.status === "loading"}
            error={scene.snapshot.feed.error}
            empty={emptyContext(scene, id, follow, writer)}
            topic={null}
          />
        ),
      };
    }
    case "topic": {
      const topic = scene.snapshot.channels.topics.find((t) => t.id === params["topic"]);
      if (topic === undefined) {
        return {
          current: { kind: "none" },
          body: (
            <Empty page title="No such topic">
              {back}
            </Empty>
          ),
        };
      }
      return {
        current: { kind: "topic", id: topic.id },
        body: (
          <FeedPage
            scene={scene}
            key={`${scene.id}/topic/${topic.id}`}
            title={topic.name}
            freshness={scene.snapshot.feed.freshness}
            entries={entriesOf(scene, topicView(scene, topic.id))}
            startOn="top"
            switchable
            writer={writer}
            loading={scene.snapshot.feed.status === "loading"}
            error={scene.snapshot.feed.error}
            empty={emptyContext(scene, "topic", follow, writer)}
            topic={{
              on: follow.on(topic),
              onToggle: () => {
                follow.toggle(topic);
              },
              keywords: topic.keywords,
            }}
          />
        ),
      };
    }
    case "group":
    case "thread": {
      const id = param(params, "group");
      const group = scene.snapshot.groups.find((g) => g.id === id);
      if (group === undefined) {
        return {
          current: { kind: "none" },
          body: (
            <Empty page title="This group does not exist or is not open to you.">
              {back}
            </Empty>
          ),
        };
      }
      const thread =
        kind === "thread"
          ? (scene.snapshot.threads.find(
              (t) => t.groupId === group.id && t.id === param(params, "thread"),
            ) ?? null)
          : undefined;
      return {
        current: { kind: "group", id },
        body: (
          <>
            <GroupPage scene={scene} group={group} writer={writer} />
            {thread === undefined ? null : (
              <ThreadPanel scene={scene} group={group} thread={thread} writer={writer} />
            )}
          </>
        ),
      };
    }
    case "digest": {
      const id = param(params, "digest");
      const digest = scene.snapshot.digests.find((d) => d.id === id);
      if (digest === undefined) {
        return {
          current: { kind: "none" },
          body: (
            <Empty page title="No such digest in this sample">
              {back}
            </Empty>
          ),
        };
      }
      return {
        current: { kind: "digest", id },
        body: <DigestPage scene={scene} digest={digest} none={<Empty title="No digest yet" />} />,
      };
    }
    case "settings":
      return { current: { kind: "settings" }, body: <NotBuilt title="Settings" /> };
  }
}

/** A page a later task builds: its title as the h1, then the empty state saying so. */
function NotBuilt({ title }: { title: string }) {
  return (
    <>
      <PageTitle>{title}</PageTitle>
      <Empty title="Not built yet" />
    </>
  );
}

export function SignalPage({
  kind,
  params,
}: {
  kind: SignalPageKind;
  params: Record<string, string>;
}) {
  const slice = readSlice(useSource().signal);
  if (slice.kind !== "ok") {
    return (
      <div className="p-8">
        <Empty page title="No Signal data in this library" />
      </div>
    );
  }
  const scene = slice.data.scenes.find((s) => s.id === params["scene"]);
  if (scene === undefined) {
    return (
      <div className="p-8">
        <Empty page title="No such sample scene">
          <EmptyState.Footer>
            <a
              className="text-sm font-semibold text-text-link"
              href={sceneHref(slice.data.scenes[0], "feed/for-you")}
            >
              Back to the sample scenes
            </a>
          </EmptyState.Footer>
        </Empty>
      </div>
    );
  }
  return <SceneView key={scene.id} scene={scene} kind={kind} params={params} />;
}

/** One scene's page: the follow state lives here, so the channel list and the page share it. */
function SceneView({
  scene,
  kind,
  params,
}: {
  scene: SignalScene;
  kind: SignalPageKind;
  params: Record<string, string>;
}) {
  // In memory only: nothing is written; a reload shows the slice's own state again.
  const [chosen, setChosen] = useState<ReadonlyMap<string, boolean>>(new Map());
  const follow: SignalFollow = {
    on: (topic) => chosen.get(topic.id) ?? topic.followed,
    toggle: (topic) => {
      setChosen(new Map(chosen).set(topic.id, !(chosen.get(topic.id) ?? topic.followed)));
    },
  };
  const { current, body } = Body({ scene, kind, params, follow });
  return (
    <SignalFrame scene={scene} current={current} follow={follow}>
      {body}
    </SignalFrame>
  );
}
