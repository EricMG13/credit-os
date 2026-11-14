import { useState } from "react";
import { BookOpen01 } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { Button } from "@/components/base/buttons/button";
import { ALL, FilterBar, NO_FILTERS, appliedLabel, type Filters } from "./parts/FilterBar";
import { IssuerCard, LoadingCard } from "./parts/IssuerCard";
import { ButtonLink } from "./parts/ButtonLink";
import { LibraryPage } from "./parts/LibraryPage";
import { RUN_START } from "./parts/links";
import type { HomeCard, IssuerCard as IssuerCardData, LibraryHome } from "./slice";

const isIssuer = (card: HomeCard): card is IssuerCardData => card.kind === "issuer";

function matches(card: IssuerCardData, f: Filters): boolean {
  return (
    card.name.toLowerCase().includes(f.search.trim().toLowerCase()) &&
    (f.sector === ALL || card.sector === f.sector) &&
    (f.pathway === ALL || card.pathway === f.pathway) &&
    (f.state === ALL || card.state === f.state)
  );
}

/** How many of the four controls narrow the list: an index into the slice's own labels. */
function applied(f: Filters): number {
  return [f.search.trim() !== "", f.sector !== ALL, f.pathway !== ALL, f.state !== ALL].filter(
    Boolean,
  ).length;
}

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
        <ButtonLink href={RUN_START}>Start a run</ButtonLink>
      </EmptyState.Footer>
    </EmptyState>
  );
}

function Cards({ home }: { home: LibraryHome }) {
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const narrowed = applied(filters) > 0;
  const shown = home.cards.filter((card) => (isIssuer(card) ? matches(card, filters) : !narrowed));
  return (
    <>
      <FilterBar
        filters={home.filters}
        values={filters}
        onChange={setFilters}
        appliedLabel={appliedLabel(home.filters.appliedLabels, applied(filters))}
      />
      {shown.length === 0 ? (
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
            <Button
              color="secondary"
              onPress={() => {
                setFilters(NO_FILTERS);
              }}
            >
              Clear filters
            </Button>
          </EmptyState.Footer>
        </EmptyState>
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
    <LibraryPage>
      {({ home }) => (
        <div className="flex flex-col gap-8">
          <div className="flex flex-wrap items-center gap-4">
            <p className="flex-1 text-body text-text-tertiary">{home.subtitle}</p>
            {home.cards.length === 0 ? null : <ButtonLink href={RUN_START}>Start a run</ButtonLink>}
          </div>
          {home.cards.length === 0 ? <NoRuns /> : <Cards home={home} />}
        </div>
      )}
    </LibraryPage>
  );
}
