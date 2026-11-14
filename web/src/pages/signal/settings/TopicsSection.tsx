// Settings, Topics (mock settings frame 4): each topic a row with its name and "N stories this
// week", its keywords as tags and the kinds it takes as tags. A topic with no keywords takes every
// story of its kinds, and says so. New topic and Edit would write, so a writer sees them disabled
// with the reason in view; a reader sees the topics and no write control (ruling 18).
import { Plus } from "@untitledui/icons";
import { Button } from "@/components/base/buttons/button";
import { Tags } from "../parts/Tags";
import type { SignalSettingsTopic } from "../slice";
import { Section } from "./Section";

const REASON_ID = "signal-topics-write-reason";

function Row({ topic, writer }: { topic: SignalSettingsTopic; writer: boolean }) {
  return (
    <li className="flex flex-wrap items-start gap-x-4 gap-y-2 border-t border-border-hairline py-4">
      <div className="w-40 shrink-0">
        <b className="block text-md font-semibold text-text-primary">{topic.name}</b>
        <small className="block text-sm text-text-tertiary">{topic.weekly}</small>
      </div>
      <div className="grid min-w-48 flex-1 gap-2">
        {topic.keywords.length === 0 ? (
          <span className="text-sm text-text-tertiary">No keywords: every story of this kind</span>
        ) : (
          <Tags tags={topic.keywords} label={`Keywords: ${topic.name}`} />
        )}
        <Tags tags={topic.kinds} label={`Kinds: ${topic.name}`} />
      </div>
      {writer ? (
        <Button
          color="tertiary"
          isDisabled
          aria-label={`Edit: ${topic.name}`}
          aria-describedby={REASON_ID}
        >
          Edit
        </Button>
      ) : null}
    </li>
  );
}

export function TopicsSection({
  topics,
  writer,
}: {
  topics: SignalSettingsTopic[];
  writer: boolean;
}) {
  return (
    <Section
      title="Topics"
      hint="A story joins a topic when its headline or summary carries one of the keywords."
      action={
        writer ? (
          <Button color="primary" iconLeading={Plus} isDisabled aria-describedby={REASON_ID}>
            New topic
          </Button>
        ) : undefined
      }
    >
      {writer ? (
        <p id={REASON_ID} className="mb-3 text-sm text-text-tertiary">
          Sample data: topics cannot be changed here.
        </p>
      ) : null}
      {topics.length === 0 ? (
        <p className="text-sm text-text-tertiary">No topics yet</p>
      ) : (
        <ul>
          {topics.map((topic) => (
            <Row key={topic.id} topic={topic} writer={writer} />
          ))}
        </ul>
      )}
    </Section>
  );
}
