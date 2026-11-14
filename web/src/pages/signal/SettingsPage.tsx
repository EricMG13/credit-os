// Settings (mock "Signal: settings"): the page's h1, the section list as vertical tabs with the side
// line, and the section beside it. Every change is in memory (state here, so it survives moving
// between sections; a reload shows the slice again); nothing is written. A reader's list holds
// Topics and Notifications only (ruling 18).
import { useState, type ReactNode } from "react";
import { Tab, TabList, Tabs } from "@/components/application/tabs/tabs";
import { sceneHref } from "./SignalFrame";
import { PageTitle } from "./parts/PageTitle";
import type { SignalScene } from "./slice";
import { GroupsSection } from "./settings/GroupsSection";
import { NotificationsSection } from "./settings/NotificationsSection";
import { AiSection } from "./settings/AiSection";
import { DigestsSection } from "./settings/DigestsSection";
import { RulesSection } from "./settings/RulesSection";
import { SourcesSection } from "./settings/SourcesSection";
import { TopicsSection } from "./settings/TopicsSection";

type SectionId =
  "groups" | "thread-rules" | "sources" | "topics" | "digests" | "notifications" | "ai";

const SECTIONS: { id: SectionId; name: string; reader: boolean }[] = [
  { id: "groups", name: "Groups", reader: false },
  { id: "thread-rules", name: "Thread rules", reader: false },
  { id: "sources", name: "Sources", reader: false },
  { id: "topics", name: "Topics", reader: true },
  { id: "digests", name: "Digests", reader: false },
  { id: "notifications", name: "Notifications", reader: true },
  { id: "ai", name: "AI and cost", reader: false },
];

export function SettingsPage({
  scene,
  section,
  writer,
  state,
}: {
  scene: SignalScene;
  /** The address's section segment: any word; an unknown one gets a stated state. */
  section: string;
  writer: boolean;
  /** An empty state with this title (the page's own, so every Signal page states itself alike). */
  state: (title: string) => ReactNode;
}) {
  const { settings } = scene.snapshot;
  const [flags, setFlags] = useState<ReadonlyMap<string, boolean>>(new Map());
  const [typed, setTyped] = useState<ReadonlyMap<string, string>>(new Map());
  const [visible, setVisible] = useState<ReadonlyMap<string, string>>(new Map());
  const listed = SECTIONS.filter((s) => writer || s.reader);
  const current = SECTIONS.find((s) => s.id === section);
  const flag = (key: string, shown: boolean) => flags.get(key) ?? shown;
  const set = (key: string, value: boolean) => {
    setFlags(new Map(flags).set(key, value));
  };

  function content(): ReactNode {
    if (current === undefined) return state("No such settings section");
    if (!writer && !current.reader) return state("This section is for writers");
    switch (current.id) {
      case "groups":
        return (
          <GroupsSection
            groups={settings.groups}
            visibility={(g) => visible.get(g.id) ?? g.visibility}
            onVisibility={(g, value) => {
              setVisible(new Map(visible).set(g.id, value));
            }}
          />
        );
      case "thread-rules":
        return (
          <RulesSection
            rules={settings.rules}
            on={(r) => flag(`rule:${r.id}`, r.on)}
            onChange={(r, value) => {
              set(`rule:${r.id}`, value);
            }}
          />
        );
      case "notifications":
        return (
          <NotificationsSection
            events={settings.notifications.events}
            on={(e, channel) => flag(`event:${e.id}:${channel}`, e[channel])}
            onChange={(e, channel, value) => {
              set(`event:${e.id}:${channel}`, value);
            }}
          />
        );
      case "sources":
        return (
          <SourcesSection sources={settings.sources} weeksHeading={settings.sourceWeeksHeading} />
        );
      case "topics":
        return <TopicsSection topics={settings.topics} writer={writer} />;
      case "digests": {
        const form = settings.digestForm;
        const field = (key: string, delivered: string) => typed.get(key) ?? delivered;
        return (
          <DigestsSection
            form={form}
            value={{
              name: field("name", form.name),
              covers: field("covers", form.covers),
              schedule: field("schedule", form.schedule),
              length: field("length", form.length),
              brief: field("brief", form.brief),
            }}
            onChange={(key, text) => {
              setTyped(new Map(typed).set(key, text));
            }}
          />
        );
      }
      case "ai":
        return <AiSection ai={settings.ai} />;
    }
  }

  return (
    <>
      <PageTitle>Settings</PageTitle>
      <div className="mt-4 grid grid-cols-1 gap-y-4 xl:grid-cols-[200px_minmax(0,1fr)] xl:gap-x-12">
        <Tabs
          orientation="vertical"
          selectedKey={current !== undefined && listed.includes(current) ? current.id : ""}
          className="w-auto"
        >
          <TabList
            aria-label="Settings sections"
            orientation="vertical"
            type="line"
            size="sm"
            className="w-full flex-row flex-wrap gap-x-4 xl:w-max xl:flex-col"
          >
            {listed.map((s) => (
              <Tab key={s.id} id={s.id} href={sceneHref(scene, `settings/${s.id}`)}>
                {s.name}
              </Tab>
            ))}
          </TabList>
        </Tabs>
        <div className="min-w-0">{content()}</div>
      </div>
    </>
  );
}
