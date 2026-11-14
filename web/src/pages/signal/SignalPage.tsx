// One Signal address: picks the scene, then what the frame holds. Pages later tasks build replace
// the "Not built yet" empty state.
import type { ReactNode } from "react";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { useSource } from "../source";
import { SignalFrame, sceneHref, type SignalCurrent } from "./SignalFrame";
import { readSlice, type SignalScene } from "./slice";

export type SignalPageKind = "feed" | "topic" | "group" | "thread" | "digest" | "settings";

const VIEWS = { "for-you": "For you", latest: "Latest", saved: "Saved" } as const;

function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <EmptyState className="py-12">
      <EmptyState.Header>
        <EmptyState.FeaturedIcon />
      </EmptyState.Header>
      <EmptyState.Content>
        <EmptyState.Title>{title}</EmptyState.Title>
      </EmptyState.Content>
      {children}
    </EmptyState>
  );
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
          body: <Empty title="No such view">{back}</Empty>,
        };
      }
      const id = view as keyof typeof VIEWS;
      return {
        current: { kind: "view", id },
        body: <h2 className="text-xl font-semibold text-text-primary">{VIEWS[id]}</h2>,
      };
    }
    case "topic": {
      const topic = scene.snapshot.channels.topics.find((t) => t.id === params["topic"]);
      if (topic === undefined) {
        return {
          current: { kind: "none" },
          body: <Empty title="No such topic">{back}</Empty>,
        };
      }
      return {
        current: { kind: "topic", id: topic.id },
        body: <h2 className="text-xl font-semibold text-text-primary">{topic.name}</h2>,
      };
    }
    case "group":
    case "thread":
      return {
        current: { kind: "group", id: param(params, "group") },
        body: <Empty title="Not built yet" />,
      };
    case "digest":
      return {
        current: { kind: "digest", id: param(params, "digest") },
        body: <Empty title="Not built yet" />,
      };
    case "settings":
      return { current: { kind: "settings" }, body: <Empty title="Not built yet" /> };
  }
}

export function SignalPage({
  kind,
  params,
}: {
  kind: SignalPageKind;
  params: Record<string, string>;
}) {
  const slice = readSlice(useSource().signal);
  if (slice.kind !== "ok") return <Empty title="No Signal data in this library" />;
  const first = slice.data.scenes[0];
  const scene = slice.data.scenes.find((s) => s.id === params["scene"]);
  if (scene === undefined) {
    return (
      <Empty title="No such sample scene">
        <EmptyState.Footer>
          <a
            className="text-sm font-semibold text-text-link"
            href={sceneHref(first, "feed/for-you")}
          >
            Back to the sample scenes
          </a>
        </EmptyState.Footer>
      </Empty>
    );
  }
  const { current, body } = Body({ scene, kind, params });
  return (
    <SignalFrame scene={scene} current={current}>
      {body}
    </SignalFrame>
  );
}
