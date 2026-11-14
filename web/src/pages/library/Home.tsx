import { useState } from "react";
import { BookOpen01 } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { Button } from "@/components/base/buttons/button";
import { ButtonGroup, ButtonGroupItem } from "@/components/base/button-group/button-group";
import {
  ALL,
  FilterBar,
  FilterSelect,
  NO_FILTERS,
  appliedLabel,
  type Filters,
} from "./parts/FilterBar";
import { IssuerList, NO_BANDS, type Bands } from "./parts/IssuerList";
import { IssuerCard, LoadingCard } from "./parts/IssuerCard";
import { LibraryPage } from "./parts/LibraryPage";
import { PAGE_NAME, PageTitle } from "./parts/PageTitle";
import { RUN_START } from "./parts/links";
import {
  MEASURES,
  type HomeCard,
  type IssuerCard as IssuerCardData,
  type LibraryHome,
} from "./slice";

const isIssuer = (card: HomeCard): card is IssuerCardData => card.kind === "issuer";

function matches(card: IssuerCardData, f: Filters): boolean {
  return (
    card.name.toLowerCase().includes(f.search.trim().toLowerCase()) &&
    (f.sector === ALL || card.sector === f.sector) &&
    (f.pathway === ALL || card.pathway === f.pathway) &&
    (f.state === ALL || card.state === f.state)
  );
}

/** How many of the search and three selects narrow the cards. */
function applied(f: Filters): number {
  return [f.search.trim() !== "", f.sector !== ALL, f.pathway !== ALL, f.state !== ALL].filter(
    Boolean,
  ).length;
}

/** Every control in use, bands included: an index into the slice's own applied labels. */
const appliedWithBands = (f: Filters, bands: Bands): number =>
  applied(f) + MEASURES.filter((key) => bands[key] !== null).length;

function NoRuns() {
  return (
    <EmptyState>
      <EmptyState.Header>
        <EmptyState.FeaturedIcon icon={BookOpen01} />
      </EmptyState.Header>
      <EmptyState.Content>
        <EmptyState.Title>No runs yet</EmptyState.Title>
        <EmptyState.Description>
          A run reads an issuer’s files and writes its report here. Start one to add the first
          issuer.
        </EmptyState.Description>
      </EmptyState.Content>
      <EmptyState.Footer>
        <Button href={RUN_START}>Start a run</Button>
      </EmptyState.Footer>
    </EmptyState>
  );
}

function NoMatch({ onClear }: { onClear: () => void }) {
  return (
    <EmptyState>
      <EmptyState.Header>
        <EmptyState.FeaturedIcon />
      </EmptyState.Header>
      <EmptyState.Content>
        <EmptyState.Title>No issuer matches</EmptyState.Title>
        <EmptyState.Description>
          Nothing in the library fits the search and filters.
        </EmptyState.Description>
      </EmptyState.Content>
      <EmptyState.Footer>
        <Button color="secondary" onPress={onClear}>
          Clear filters
        </Button>
      </EmptyState.Footer>
    </EmptyState>
  );
}

/** One range select per measure, over the bands the slice delivers. */
function RangeFilters({
  home,
  bands,
  onChange,
}: {
  home: LibraryHome;
  bands: Bands;
  onChange: (next: Bands) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {MEASURES.map((key) => {
        const spec = home.list.measures[key];
        const chosen = bands[key];
        const chosenBand = chosen === null ? undefined : spec.bands[chosen];
        if (chosen !== null && chosenBand === undefined) {
          throw new RangeError(`no band ${String(chosen)} for ${key}`);
        }
        return (
          <FilterSelect
            key={key}
            name={spec.name}
            options={spec.bands.map((band) => band.label)}
            value={chosenBand === undefined ? ALL : chosenBand.label}
            onChange={(label) => {
              const index = spec.bands.findIndex((band) => band.label === label);
              onChange({ ...bands, [key]: index < 0 ? null : index });
            }}
          />
        );
      })}
    </div>
  );
}

function Layout({ home }: { home: LibraryHome }) {
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [bands, setBands] = useState<Bands>(NO_BANDS);
  const [layout, setLayout] = useState<"cards" | "list">("cards");
  const narrowed = applied(filters) > 0;
  const shown = home.cards.filter((card) => (isIssuer(card) ? matches(card, filters) : !narrowed));
  const clear = () => {
    setFilters(NO_FILTERS);
    setBands(NO_BANDS);
  };
  return (
    <>
      <FilterBar
        filters={home.filters}
        values={filters}
        onChange={setFilters}
        appliedLabel={appliedLabel(home.filters.appliedLabels, appliedWithBands(filters, bands))}
      >
        <ButtonGroup
          aria-label="Layout"
          size="sm"
          disallowEmptySelection
          selectedKeys={[layout]}
          onSelectionChange={(keys) => {
            const [key] = keys;
            if (key === "cards") setBands(NO_BANDS);
            if (key === "cards" || key === "list") setLayout(key);
          }}
        >
          <ButtonGroupItem id="cards">Cards</ButtonGroupItem>
          <ButtonGroupItem id="list">List</ButtonGroupItem>
        </ButtonGroup>
      </FilterBar>
      {layout === "list" ? (
        <>
          <RangeFilters home={home} bands={bands} onChange={setBands} />
          <IssuerList
            home={home}
            rows={shown.filter(isIssuer)}
            bands={bands}
            empty={<NoMatch onClear={clear} />}
          />
        </>
      ) : shown.length === 0 ? (
        <NoMatch onClear={clear} />
      ) : (
        <div className="grid grid-cols-1 gap-6 min-[800px]:grid-cols-2 min-[1200px]:grid-cols-3">
          {shown.map((card, index) =>
            isIssuer(card) ? (
              <IssuerCard key={card.issuer} card={card} />
            ) : (
              <LoadingCard key={`loading-${String(index)}`} />
            ),
          )}
        </div>
      )}
    </>
  );
}

/** The library home: the delivered cards, narrowed in memory by search and three filters. */
export function Home() {
  return (
    <LibraryPage title={PAGE_NAME.home}>
      {({ home }) => (
        <div className="flex flex-col gap-8">
          <div className="flex flex-wrap items-start gap-4 border-b border-secondary pb-4">
            <div className="flex min-w-0 flex-1 flex-col gap-1.5">
              <PageTitle>{PAGE_NAME.home}</PageTitle>
              <p className="text-body text-text-tertiary">{home.subtitle}</p>
            </div>
            {home.cards.length === 0 ? null : <Button href={RUN_START}>Start a run</Button>}
          </div>
          {home.cards.length === 0 ? <NoRuns /> : <Layout home={home} />}
        </div>
      )}
    </LibraryPage>
  );
}
