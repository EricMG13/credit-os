import { SearchLg } from "@untitledui/icons";
import { Input } from "@/components/base/input/input";
import { Select } from "@/components/base/select/select";

const SCHEDULES = ["Quarterly", "Semi-annual", "Annual"];

function Heading({ id, children }: { id: string; children: string }) {
  return (
    <h2 id={id} className="font-display text-h2 text-text-primary">
      {children}
    </h2>
  );
}

/** The kit's input and select sections: default, invalid with a message, disabled. */
export function KitInputSelect() {
  return (
    <>
      <section aria-labelledby="kit-input" className="mt-8 flex flex-col gap-4">
        <Heading id="kit-input">Input</Heading>
        <div className="flex max-w-sm flex-col gap-4">
          <Input label="Issuer name" hint="As it appears on the cover page." placeholder="Issuer" />
          <Input
            label="Reporting currency"
            hint="Use a three-letter code, for example USD."
            isInvalid
            defaultValue="US"
          />
          <Input label="Registry number" icon={SearchLg} isDisabled defaultValue="Not editable" />
        </div>
      </section>

      <section aria-labelledby="kit-select" className="mt-8 flex flex-col gap-4">
        <Heading id="kit-select">Select</Heading>
        <div className="flex max-w-sm flex-col gap-4">
          <Select label="Update schedule" hint="How often the library refreshes.">
            {SCHEDULES.map((name) => (
              <Select.Item key={name} id={name} label={name} />
            ))}
          </Select>
          <Select label="Archive window" isDisabled defaultValue="Annual">
            {SCHEDULES.map((name) => (
              <Select.Item key={name} id={name} label={name} />
            ))}
          </Select>
          <Select label="Review cycle" hint="Choose a cycle to continue." isInvalid>
            {SCHEDULES.map((name) => (
              <Select.Item key={name} id={name} label={name} />
            ))}
          </Select>
        </div>
      </section>
    </>
  );
}
