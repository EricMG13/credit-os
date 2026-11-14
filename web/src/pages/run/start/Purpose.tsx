import { useId, useState } from "react";
import { RadioButton, RadioField, RadioGroup } from "react-aria-components";
import { Check, FileCheck02 } from "@untitledui/icons";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { cx } from "@/utils/cx";
import type { StartDraft } from "../slice";

type Step = Extract<StartDraft, { step: "purpose" }>;

// Kit candidate: radio cards (header strip with icon, title and a check control; body with the
// description and a small label).
/** The Purpose step: one card per purpose; the choice lives in memory only. */
export function Purpose({
  chosen,
  purposes,
}: {
  chosen: Step["chosen"];
  purposes: Step["purposes"];
}) {
  const headingId = useId();
  const [selected, setSelected] = useState<string | null>(chosen);
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 id={headingId} className="font-display text-h3 text-text-primary">
          Purpose
        </h2>
        <p className="text-sm text-text-secondary">
          The purpose decides which modules run, and so how much of the cap the run can use.
        </p>
      </div>
      <RadioGroup
        aria-labelledby={headingId}
        value={selected}
        onChange={setSelected}
        className="flex flex-col gap-3"
      >
        {purposes.map((p) => (
          <RadioField key={p.id} value={p.id}>
            <RadioButton
              className={({ isSelected, isFocusVisible }) =>
                cx(
                  "block cursor-pointer rounded-xl bg-primary ring-1 ring-secondary ring-inset outline-none",
                  isSelected && "ring-2 ring-brand",
                  isFocusVisible && "outline-2 outline-offset-2 outline-brand",
                )
              }
            >
              {({ isSelected }) => (
                <>
                  <div className="flex items-center gap-3 rounded-t-xl py-3 pr-5 pl-3">
                    <FeaturedIcon icon={FileCheck02} color="brand" size="md" />
                    <span className="text-md font-semibold text-secondary">{p.title}</span>
                    <span
                      aria-hidden="true"
                      className={cx(
                        "ml-auto flex size-4 flex-none items-center justify-center rounded text-white ring-1 ring-primary ring-inset",
                        isSelected && "bg-brand-solid ring-brand",
                      )}
                    >
                      {isSelected ? <Check className="size-3" strokeWidth={3} /> : null}
                    </span>
                  </div>
                  <div className="flex items-start justify-between gap-4 p-4">
                    <p className="text-sm text-tertiary">{p.description}</p>
                    <span className="flex-none rounded-md bg-primary px-1.5 py-0.5 text-xs font-medium whitespace-nowrap text-secondary ring-1 ring-primary ring-inset">
                      {p.modules}
                    </span>
                  </div>
                </>
              )}
            </RadioButton>
          </RadioField>
        ))}
      </RadioGroup>
    </div>
  );
}
