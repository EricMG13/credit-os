// Settings, Digests (mock settings frame 5): the digest form: its name, what it covers, its
// schedule, its length and a brief. Every field is edited in memory. Save and Run once now would
// write or call a paid model (decision 0006 ruling 21, decision 0003 ruling 9), so they are
// disabled with the reason in view; the frame labels them "Save digest" and "Run once now".
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { Select } from "@/components/base/select/select";
import { TextArea } from "../parts/TextArea";
import type { SignalDigestForm } from "../slice";
import { Section } from "./Section";

const SAVE_ID = "signal-digest-save-reason";
const RUN_ID = "signal-digest-run-reason";

function Choice({
  label,
  hint,
  options,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <Select
      label={label}
      hint={hint}
      items={options.map((id) => ({ id, label: id }))}
      value={value}
      onChange={(key) => {
        onChange(String(key));
      }}
    >
      {(item) => <Select.Item id={item.id} label={item.label} />}
    </Select>
  );
}

export function DigestsSection({
  form,
  value,
  onChange,
}: {
  form: SignalDigestForm;
  /** The form's current values (the delivered ones until a field is edited). */
  value: Record<"name" | "covers" | "schedule" | "length" | "brief", string>;
  onChange: (field: keyof typeof value, text: string) => void;
}) {
  return (
    <Section
      title={form.name}
      hint="A digest is written by a model from the stories it covers, on its schedule."
    >
      <div className="flex max-w-[640px] flex-col gap-5">
        <Input
          label="Name"
          value={value.name}
          onChange={(text) => {
            onChange("name", text);
          }}
        />
        <Choice
          label="Covers"
          hint="A group's topics, or a single topic."
          options={form.coversOptions}
          value={value.covers}
          onChange={(text) => {
            onChange("covers", text);
          }}
        />
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <Choice
            label="Schedule"
            options={form.scheduleOptions}
            value={value.schedule}
            onChange={(text) => {
              onChange("schedule", text);
            }}
          />
          <Choice
            label="Length"
            options={form.lengthOptions}
            value={value.length}
            onChange={(text) => {
              onChange("length", text);
            }}
          />
        </div>
        <TextArea
          label="Brief (optional)"
          hint="Plain text. Tell the model what matters to this group."
          rows={3}
          value={value.brief}
          onChange={(text) => {
            onChange("brief", text);
          }}
        />
        <div className="flex flex-wrap justify-end gap-3">
          <Button color="secondary" isDisabled aria-describedby={RUN_ID}>
            Run once now
          </Button>
          <Button color="primary" isDisabled aria-describedby={SAVE_ID}>
            Save digest
          </Button>
        </div>
        <p id={RUN_ID} className="text-sm text-text-tertiary">
          Running a digest calls a paid model. It stays off until the owner sets a cap.
        </p>
        <p id={SAVE_ID} className="-mt-3 text-sm text-text-tertiary">
          Sample data: digests cannot be saved here.
        </p>
      </div>
    </Section>
  );
}
