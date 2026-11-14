import { useState } from "react";
import { FilterLines } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { Button } from "@/components/base/buttons/button";
import type { Reader } from "../slice";
import { ALL, FilterSelect } from "./FilterBar";
import { SUBSECTION_HEADING } from "./heading";

/**
 * The module filter of an Evidence tab whose content is delivered per module: page state, in memory,
 * so a tab starts at "All". Its options are the delivered module names; what is compared is the id.
 */
export function useModuleFilter(options: readonly Reader[]) {
  const [name, setName] = useState(ALL);
  return {
    chosen: options.find((option) => option.name === name) ?? null,
    clear: () => {
      setName(ALL);
    },
    control: (
      <FilterSelect
        name="Module"
        options={options.map((option) => option.name)}
        value={name}
        onChange={setName}
      />
    ),
  };
}

/** What a tab draws when the chosen module holds nothing of it: what is missing and the way back. */
export function NothingForModule({
  title,
  clearLabel,
  onClear,
}: {
  title: string;
  clearLabel: string;
  onClear: () => void;
}) {
  return (
    <EmptyState>
      <EmptyState.Header>
        <EmptyState.FeaturedIcon icon={FilterLines} />
      </EmptyState.Header>
      <EmptyState.Content>
        <EmptyState.Title as={SUBSECTION_HEADING}>{title}</EmptyState.Title>
        <EmptyState.Description>Choose another module, or all of them.</EmptyState.Description>
      </EmptyState.Content>
      <EmptyState.Footer>
        <Button color="secondary" onPress={onClear}>
          {clearLabel}
        </Button>
      </EmptyState.Footer>
    </EmptyState>
  );
}
