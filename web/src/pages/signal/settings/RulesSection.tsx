// Settings, Thread rules (mock settings frame 2): one switch per rule with its label and hint.
// The rules are the mock's examples (mock question 11); a switch changes in memory only.
import type { SignalSettingsRule } from "../slice";
import { Toggle } from "../parts/Toggle";
import { Section } from "./Section";

export function RulesSection({
  rules,
  on,
  onChange,
}: {
  rules: SignalSettingsRule[];
  on: (rule: SignalSettingsRule) => boolean;
  onChange: (rule: SignalSettingsRule, value: boolean) => void;
}) {
  return (
    <Section title="Thread rules" hint="These apply to every group.">
      {rules.length === 0 ? (
        <p className="text-sm text-text-tertiary">No thread rules yet.</p>
      ) : (
        <ul className="flex flex-col gap-5">
          {rules.map((rule) => (
            <li key={rule.id}>
              <Toggle
                label={rule.label}
                hint={rule.hint}
                isSelected={on(rule)}
                onChange={(value) => {
                  onChange(rule, value);
                }}
              />
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}
