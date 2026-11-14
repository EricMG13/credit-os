// The layout every Signal page sits in: the channel list on the left, the page's content on the
// right, each scrolling on its own, filling the full-bleed page region after mock/signal.js (SgShell) and `.sub`, `.ni`, `.cnt`, `.dot`, `.me`.
import { useId, useRef, type FC, type ReactNode } from "react";
import {
  Bookmark,
  Clock,
  File05,
  Hash02,
  Sliders04,
  Star01,
  Stars01,
  Users01,
} from "@untitledui/icons";
import { Badge } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { ButtonUtility } from "@/components/base/buttons/button-utility";
import { StatusBadge } from "@/components/status/StatusBadge";
import { cx } from "@/utils/cx";
import { AvatarLabelGroup } from "./parts/Avatar";
import type { SignalScene } from "./slice";

/** Which channel the page is on; the item with the same key is marked current. */
export type SignalCurrent =
  | { kind: "view"; id: "for-you" | "latest" | "saved" }
  | { kind: "topic" | "group" | "digest"; id: string }
  | { kind: "settings" }
  /** The address names no channel item (an unknown view or topic): nothing is marked current. */
  | { kind: "none" };

/** Follow state kept above the frame so the channel list and the page agree; in memory only. */
export type SignalFollow = {
  on: (topic: { id: string; followed: boolean }) => boolean;
  toggle: (topic: { id: string; followed: boolean }) => void;
};

export function sceneHref(scene: SignalScene, path: string): string {
  return `#/signal/${encodeURIComponent(scene.id)}/${path}`;
}

function isCurrent(current: SignalCurrent, kind: SignalCurrent["kind"], id?: string): boolean {
  if (current.kind !== kind || current.kind === "none") return false;
  return current.kind === "settings" || current.id === id;
}

type RowProps = {
  href: string;
  icon: FC<{ className?: string }>;
  on: boolean;
  children: ReactNode;
};

function Row({
  href,
  icon: Icon,
  on,
  children,
  mark,
  after,
}: RowProps & { mark?: ReactNode; after?: ReactNode }) {
  return (
    <li
      className={cx(
        "my-px flex min-h-9 items-center py-1.5 rounded-ds-xs px-2 text-sm font-semibold",
        on ? "bg-surface-selected text-text-link" : "text-text-secondary",
      )}
    >
      <a
        href={href}
        aria-current={on ? "page" : undefined}
        className="flex min-w-0 flex-1 items-center gap-2 outline-focus-ring focus-visible:outline-2"
      >
        <Icon className={cx("size-4 shrink-0", on ? "text-text-link" : "text-fg-quaternary")} />
        <span className="min-w-0 flex-1">{children}</span> {mark}
      </a>
      {after}
    </li>
  );
}

const Count = ({ children }: { children: ReactNode }) => (
  <Badge size="sm" className="ml-3">
    {children}
  </Badge>
);

function Heading({ children }: { children: string }) {
  return <h2 className="px-2 pt-4 pb-1 text-xs font-bold text-text-tertiary">{children}</h2>;
}

function ChannelList({
  scene,
  current,
  follow,
}: {
  scene: SignalScene;
  current: SignalCurrent;
  follow: SignalFollow;
}) {
  const { channels } = scene.snapshot;
  const headingId = useId();
  const views = [
    { id: "for-you", label: "For you", icon: Stars01, count: null },
    { id: "latest", label: "Latest", icon: Clock, count: null },
    { id: "saved", label: "Saved", icon: Bookmark, count: channels.savedCount },
  ] as const;
  return (
    <nav
      aria-labelledby={headingId}
      className="flex h-full w-64 shrink-0 flex-col overflow-y-auto border-r-[1.5px] border-border-hairline bg-surface-card px-4 pt-6 pb-5"
    >
      <h2 id={headingId} className="px-2 text-sm font-semibold text-text-link">
        Signal
      </h2>
      <ul className="pt-2">
        {views.map((view) => (
          <Row
            key={view.id}
            href={sceneHref(scene, `feed/${view.id}`)}
            icon={view.icon}
            on={isCurrent(current, "view", view.id)}
            mark={view.count === null ? undefined : <Count>{view.count}</Count>}
          >
            {view.label}
          </Row>
        ))}
      </ul>
      <Heading>Topics</Heading>
      {channels.topics.length === 0 ? (
        <p className="px-2 py-2 text-sm text-text-tertiary">No topics yet</p>
      ) : (
        <ul>
          {channels.topics.map((topic) => {
            const on = follow.on(topic);
            return (
              <Row
                key={topic.id}
                href={sceneHref(scene, `topic/${topic.id}`)}
                icon={Hash02}
                on={isCurrent(current, "topic", topic.id)}
                mark={<Count>{topic.count ?? "n.a."}</Count>}
                after={
                  <ButtonUtility
                    tooltip={`${on ? "Unfollow" : "Follow"} ${topic.name}`}
                    aria-pressed={on}
                    className={on ? "text-action hover:text-action-hover" : undefined}
                    icon={<Star01 data-icon className={on ? "fill-current" : undefined} />}
                    onPress={() => {
                      follow.toggle(topic);
                    }}
                  />
                }
              >
                {topic.name}
              </Row>
            );
          })}
        </ul>
      )}
      <Heading>Groups</Heading>
      <ul>
        {channels.groups.map((group) => (
          <Row
            key={group.id}
            href={sceneHref(scene, `group/${group.id}`)}
            icon={Users01}
            on={isCurrent(current, "group", group.id)}
            mark={group.unread === null ? undefined : <Count>{group.unread}</Count>}
          >
            {group.name}
          </Row>
        ))}
      </ul>
      <Heading>Digests</Heading>
      <ul>
        {channels.digests.map((digest) => (
          <Row
            key={digest.id}
            href={sceneHref(scene, `digest/${digest.id}`)}
            icon={File05}
            on={isCurrent(current, "digest", digest.id)}
            mark={<DigestMark paused={digest.paused} unread={digest.unread} />}
          >
            {digest.name}
          </Row>
        ))}
      </ul>
      <ul className="mt-2">
        <Row
          href={sceneHref(scene, "settings/topics")}
          icon={Sliders04}
          on={isCurrent(current, "settings")}
        >
          Settings
        </Row>
      </ul>
      <NameChip viewer={scene.snapshot.viewer} />
    </nav>
  );
}

function DigestMark({ paused, unread }: { paused: boolean; unread: boolean }) {
  if (paused) {
    return (
      <span className="ml-2 *:text-xs!">
        <StatusBadge set="Signal source states" state="Paused" />
      </span>
    );
  }
  if (!unread) return null;
  return (
    <span className="ml-3 size-2 shrink-0 rounded-full bg-action">
      <span className="sr-only">Unread</span>
    </span>
  );
}

/** Ruling 19: the viewer's name and role; with no name, a button to set one (the dialog is task 6). */
function NameChip({ viewer }: { viewer: SignalScene["snapshot"]["viewer"] }) {
  return (
    <div className="mt-auto pt-4">
      <AvatarLabelGroup
        size="sm"
        initials={viewer.initials}
        own={viewer.name !== null}
        title={
          viewer.name ?? (
            <Button color="link-color" size="sm">
              Set your name
            </Button>
          )
        }
        subtitle={viewer.roleLabel}
      />
    </div>
  );
}

export function SignalFrame({
  scene,
  current,
  follow,
  children,
}: {
  scene: SignalScene;
  current: SignalCurrent;
  follow: SignalFollow;
  children: ReactNode;
}) {
  const content = useRef<HTMLDivElement>(null);
  return (
    <div className="flex h-full">
      <a
        href="#signal-content"
        className="sr-only outline-focus-ring focus:not-sr-only focus:outline-2 focus:outline-offset-2 focus:fixed focus:top-2 focus:left-2 focus:z-10 focus:rounded-ds-xs focus:bg-surface-card focus:p-2 focus:text-text-link"
        onClick={(event) => {
          event.preventDefault();
          content.current?.focus();
        }}
      >
        Skip to the feed
      </a>
      <ChannelList scene={scene} current={current} follow={follow} />
      <div
        id="signal-content"
        ref={content}
        tabIndex={-1}
        className="min-w-0 flex-1 overflow-y-auto p-8 outline-none"
      >
        {children}
      </div>
    </div>
  );
}
