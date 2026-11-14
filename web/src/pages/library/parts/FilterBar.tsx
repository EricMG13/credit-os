import { SearchLg } from "@untitledui/icons";
import { Input } from "@/components/base/input/input";
import { Select } from "@/components/base/select/select";
import type { LibraryHome } from "../slice";

export const ALL = "all";
export type Filters = { search: string; sector: string; pathway: string; state: string };
export const NO_FILTERS: Filters = { search: "", sector: ALL, pathway: ALL, state: ALL };

const optionId = (option: string) => `option:${option}`;

function FilterSelect({
  name,
  options,
  value,
  onChange,
}: {
  name: string;
  options: readonly string[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <Select
      aria-label={name}
      className="w-60"
      value={value === ALL ? ALL : optionId(value)}
      onChange={(key) => {
        const id = String(key);
        onChange(id === ALL ? ALL : id.slice("option:".length));
      }}
    >
      <Select.Item id={ALL} label={`${name}: All`} />
      {options.map((option) => (
        <Select.Item key={option} id={optionId(option)} label={`${name}: ${option}`} />
      ))}
    </Select>
  );
}

/** Search and three selects; `appliedLabel` is the slice's own words for how many are in use. */
export function FilterBar({
  filters,
  values,
  onChange,
  appliedLabel,
}: {
  filters: LibraryHome["filters"];
  values: Filters;
  onChange: (next: Filters) => void;
  appliedLabel: string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="w-72">
        <Input
          icon={SearchLg}
          placeholder="Search issuers"
          value={values.search}
          onChange={(search) => {
            onChange({ ...values, search });
          }}
        />
      </div>
      <FilterSelect
        name="Sector"
        options={filters.sector}
        value={values.sector}
        onChange={(sector) => {
          onChange({ ...values, sector });
        }}
      />
      <FilterSelect
        name="Pathway"
        options={filters.pathway}
        value={values.pathway}
        onChange={(pathway) => {
          onChange({ ...values, pathway });
        }}
      />
      <FilterSelect
        name="State"
        options={filters.state}
        value={values.state}
        onChange={(state) => {
          onChange({ ...values, state });
        }}
      />
      <span className="ml-auto text-small text-text-tertiary">{appliedLabel}</span>
    </div>
  );
}
