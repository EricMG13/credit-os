import { createContext, useContext, useState, type ReactNode } from "react";
import { SwitchButton, SwitchField } from "react-aria-components";

const ShowSourcesContext = createContext<boolean | null>(null);
const SetShowSourcesContext = createContext<((on: boolean) => void) | null>(null);

/** Holds the "Show sources" state, in memory and off by default, for the controls beneath it. */
export function ShowSources({ children }: { children: ReactNode }) {
  const [on, setOn] = useState(false);
  return (
    <ShowSourcesContext.Provider value={on}>
      <SetShowSourcesContext.Provider value={setOn}>{children}</SetShowSourcesContext.Provider>
    </ShowSourcesContext.Provider>
  );
}

/** Whether every trace control is shown. */
export function useShowSources(): boolean {
  const on = useContext(ShowSourcesContext);
  if (on === null) throw new Error("useShowSources was called outside ShowSources");
  return on;
}

export function ShowSourcesSwitch() {
  const on = useShowSources();
  const setOn = useContext(SetShowSourcesContext);
  if (setOn === null) throw new Error("ShowSourcesSwitch was called outside ShowSources");
  return (
    <SwitchField isSelected={on} onChange={setOn}>
      <SwitchButton className="group inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-text-secondary">
        <span className="relative h-5 w-9 flex-none rounded-full border border-border-control bg-surface-card transition-colors duration-150 group-data-[selected]:border-action group-data-[selected]:bg-action group-data-[focus-visible]:outline-2 group-data-[focus-visible]:outline-offset-2 group-data-[focus-visible]:outline-focus motion-reduce:transition-none">
          <span className="absolute top-0.5 left-0.5 size-3.5 rounded-full bg-border-control transition-[left] duration-150 group-data-[selected]:left-[18px] group-data-[selected]:bg-surface-card motion-reduce:transition-none" />
        </span>
        Show sources
      </SwitchButton>
    </SwitchField>
  );
}
