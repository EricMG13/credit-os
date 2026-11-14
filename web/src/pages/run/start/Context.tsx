import { useState } from "react";
import { TextArea, TextField } from "react-aria-components";
import { HintText } from "@/components/base/input/hint-text";
import { Label } from "@/components/base/input/label";

// Kit candidate: a multi-line field; the kit's Input is single-line.
/** The More context step: an optional note, held in memory only. */
export function Context({ note }: { note: string }) {
  const [value, setValue] = useState(note);
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="font-display text-h3 text-text-primary">More context</h2>
        <p className="text-sm text-text-secondary">
          Optional. Skip this step if the documents say everything.
        </p>
      </div>
      <TextField value={value} onChange={setValue} className="group flex flex-col gap-1.5">
        <Label>Anything the analysis should know</Label>
        <TextArea
          rows={6}
          placeholder="For example: the committee wants a view on the 2028 maturities; the scanned presentation was left out."
          className="min-h-36 w-full rounded-lg bg-primary px-3.5 py-3 text-md text-primary shadow-xs ring-1 ring-primary ring-inset outline-none placeholder:text-placeholder focus:ring-2 focus:ring-brand"
        />
        <HintText>
          What helps: the question behind this run, events after the latest report, documents you
          chose to leave out. Do not paste material from a private source.{" "}
          <span className="block">
            Not saved here: this page shows a saved example and is not connected to the run service.
          </span>
        </HintText>
      </TextField>
    </div>
  );
}
