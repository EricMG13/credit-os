import { BookOpen01 } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { ButtonLink } from "./parts/ButtonLink";
import { IssuerCard, LoadingCard } from "./parts/IssuerCard";
import { LibraryPage } from "./parts/LibraryPage";
import { RUN_START } from "./parts/links";

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

/** The library home: the delivered cards, each a link to its issuer's latest run. */
export function Home() {
  return (
    <LibraryPage>
      {({ home }) => (
        <div className="flex flex-col gap-8">
          <div className="flex flex-wrap items-center gap-4">
            <p className="flex-1 text-body text-text-tertiary">{home.subtitle}</p>
            {home.cards.length === 0 ? null : <ButtonLink href={RUN_START}>Start a run</ButtonLink>}
          </div>
          {home.cards.length === 0 ? (
            <NoRuns />
          ) : (
            <div className="grid grid-cols-1 gap-6 min-[800px]:grid-cols-2 min-[1200px]:grid-cols-3">
              {home.cards.map((card, index) =>
                card.kind === "issuer" ? (
                  <IssuerCard key={card.issuer} card={card} />
                ) : (
                  <LoadingCard key={`loading-${String(index)}`} />
                ),
              )}
            </div>
          )}
        </div>
      )}
    </LibraryPage>
  );
}
