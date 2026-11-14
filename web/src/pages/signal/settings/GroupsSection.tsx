// Settings, Groups (mock settings frame 1): each group a row with its avatar and member line, its
// members' avatars (or "Add a member to start"), a Select for who can see it, and Edit members.
// The visibility is changed in memory only. New group and Edit members would write; the sample has
// no service, so they are disabled with the reason in view.
import { Plus, Users01 } from "@untitledui/icons";
import { Button } from "@/components/base/buttons/button";
import { Select } from "@/components/base/select/select";
import { AvatarLabelGroup } from "../parts/Avatar";
import { AvatarGroup } from "../parts/AvatarGroup";
import type { SignalSettingsGroup } from "../slice";
import { Section } from "./Section";

const REASON_ID = "signal-groups-write-reason";

function Row({
  group,
  visibility,
  onVisibility,
}: {
  group: SignalSettingsGroup;
  visibility: string;
  onVisibility: (value: string) => void;
}) {
  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-3 border-t border-border-hairline py-4">
      <div className="min-w-48 flex-1">
        <AvatarLabelGroup
          size="md"
          initials={null}
          icon={Users01}
          title={group.name}
          subtitle={group.memberSummary}
        />
      </div>
      {group.members.length === 0 ? (
        <span className="text-sm text-text-tertiary">Add a member to start</span>
      ) : (
        <>
          <AvatarGroup monograms={group.members.map((m) => m.initials)} more={group.moreMembers} />
          <ul aria-label={`Members of ${group.name}`} className="sr-only">
            {group.members.map((m) => (
              <li key={m.name}>{m.name}</li>
            ))}
          </ul>
        </>
      )}
      <Select
        aria-label={`Visibility: ${group.name}`}
        className="w-50"
        items={group.visibilityOptions.map((id) => ({ id, label: id }))}
        value={visibility}
        onChange={(key) => {
          onVisibility(String(key));
        }}
      >
        {(item) => <Select.Item id={item.id} label={item.label} />}
      </Select>
      <Button color="tertiary" isDisabled aria-describedby={REASON_ID}>
        Edit members
        <span className="sr-only">{`: ${group.name}`}</span>
      </Button>
    </li>
  );
}

export function GroupsSection({
  groups,
  visibility,
  onVisibility,
}: {
  groups: SignalSettingsGroup[];
  visibility: (group: SignalSettingsGroup) => string;
  onVisibility: (group: SignalSettingsGroup, value: string) => void;
}) {
  return (
    <Section
      title="Groups"
      hint="A group has a thread for every story shared to it."
      action={
        <Button color="primary" iconLeading={Plus} isDisabled aria-describedby={REASON_ID}>
          New group
        </Button>
      }
    >
      <p id={REASON_ID} className="mb-3 text-sm text-text-tertiary">
        Sample data: groups and their members cannot be changed here.
      </p>
      {groups.length === 0 ? <p className="text-sm text-text-tertiary">No groups yet.</p> : null}
      <ul>
        {groups.map((group) => (
          <Row
            key={group.id}
            group={group}
            visibility={visibility(group)}
            onVisibility={(value) => {
              onVisibility(group, value);
            }}
          />
        ))}
      </ul>
    </Section>
  );
}
