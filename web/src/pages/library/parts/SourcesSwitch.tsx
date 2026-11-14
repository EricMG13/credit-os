import { SwitchButton, SwitchField } from "react-aria-components";

/** The page-level "Show sources" switch (Untitled UI toggle look); the kit's toggle replaces this file. */
export function SourcesSwitch({
  isSelected,
  onChange,
}: {
  isSelected: boolean;
  onChange: (on: boolean) => void;
}) {
  return (
    <SwitchField isSelected={isSelected} onChange={onChange}>
      <SwitchButton className="group inline-flex cursor-pointer items-center gap-2 text-small font-medium text-text-secondary outline-hidden">
        <span className="flex h-5 w-9 flex-none rounded-ds-full bg-border-control p-0.5 transition-colors duration-150 group-selected:bg-action group-focus-visible:ring-2 group-focus-visible:ring-focus group-focus-visible:ring-offset-2 motion-reduce:transition-none">
          <span className="size-4 rounded-ds-full bg-white shadow-sm transition-transform duration-150 group-selected:translate-x-4 motion-reduce:transition-none" />
        </span>
        Show sources
      </SwitchButton>
    </SwitchField>
  );
}
