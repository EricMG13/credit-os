// One Signal address: picks the scene, then what the frame holds. Pages later tasks build replace
// the "Not built yet" empty state.
import type { ReactNode } from "react";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { useSource } from "../source";
import { SignalFrame, sceneHref, type SignalCurrent } from "./SignalFrame";
import { FeedPage, type FeedEntry } from "./FeedPage";
import { PageTitle } from "./parts/PageTitle";
import { readSlice, type SignalScene } from "./slice";

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
      { kind: "digest", digest, href: sceneHref(scene, `digest/${encodeURIComponent(digest.id)}`) },
    ]),
  ]);
  return ids.map((id) => {
    const entry = byId.get(id);
    if (entry === undefined)
      throw new Error(`the slice reader let through an unknown entry "${id}"`);
    return entry;
  });
}

/** The reader gives every channel topic an order; a missing one is a wiring fault, so it is loud. */
function topicOrder(scene: SignalScene, id: string): string[] {
  const { topics } = scene.snapshot.feed;
  const order = Object.hasOwn(topics, id) ? topics[id] : undefined;
  if (order === undefined)
    throw new Error(`the slice reader let through topic "${id}" with no order`);
  return order.top;
}

/** The route pattern guarantees these segments; a missing one is a wiring fault, so it is loud. */
function param(params: Record<string, string>, name: string): string {
  const value = params[name];
  if (value === undefined) throw new Error(`the route gave no "${name}" segment`);
  return value;
}

function Body({
  scene,
  kind,
  params,
}: {
  scene: SignalScene;
  kind: SignalPageKind;
  params: Record<string, string>;
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
            title={VIEWS[id]}
            entries={ordered(scene, scene.snapshot.feed.views[id].top)}
            writer={scene.snapshot.viewer.role === "writer"}
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
            title={topic.name}
            entries={ordered(scene, topicOrder(scene, topic.id))}
            writer={scene.snapshot.viewer.role === "writer"}
          />
        ),
      };
    }
    case "group":
    case "thread": {
      const id = param(params, "group");
      const group = scene.snapshot.channels.groups.find((g) => g.id === id);
      if (group === undefined) {
        return {
          current: { kind: "none" },
          body: (
            <Empty page title="No such group">
              {back}
            </Empty>
          ),
        };
      }
      return { current: { kind: "group", id }, body: <NotBuilt title={group.name} /> };
    }
    case "digest": {
      const id = param(params, "digest");
      const digest = scene.snapshot.channels.digests.find((d) => d.id === id);
      if (digest === undefined) {
        return {
          current: { kind: "none" },
          body: (
            <Empty page title="No such digest">
              {back}
            </Empty>
          ),
        };
      }
      return { current: { kind: "digest", id }, body: <NotBuilt title={digest.name} /> };
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
            <a className="text-sm font-semibold text-text-link" href="#/signal">
              Back to the sample scenes
            </a>
          </EmptyState.Footer>
        </Empty>
      </div>
    );
  }
  const { current, body } = Body({ scene, kind, params });
  return (
    <SignalFrame scene={scene} current={current}>
      {body}
    </SignalFrame>
  );
}
