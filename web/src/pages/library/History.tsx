import { Link } from "react-aria-components";
import { BookOpen01 } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { PageHeader } from "@/shell/PageHeader";
import { ButtonLink } from "./parts/ButtonLink";
import { LibraryPage } from "./parts/LibraryPage";
import { RunFeed } from "./parts/RunFeed";
import { ISSUER_HEADING } from "./parts/heading";
import { LIBRARY_HOME, RUN_START, TEXT_LINK, overviewHref } from "./parts/links";
import type { Issuer } from "./slice";

function Missing() {
  return (
    <EmptyState>
      <EmptyState.Header>
        <EmptyState.FeaturedIcon icon={BookOpen01} />
      </EmptyState.Header>
      <EmptyState.Content>
        <EmptyState.Title>No such issuer</EmptyState.Title>
        <EmptyState.Description>
          The library holds no issuer at this address.
        </EmptyState.Description>
      </EmptyState.Content>
      <EmptyState.Footer>
        <ButtonLink href={LIBRARY_HOME} color="secondary">
          Back to the library
        </ButtonLink>
      </EmptyState.Footer>
    </EmptyState>
  );
}

function NoReport({ issuer, sentence }: { issuer: Issuer; sentence: string }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <PageHeader as={ISSUER_HEADING} title={issuer.name} />
        <p className="text-body text-text-tertiary">{issuer.history.subtitle}</p>
      </div>
      <EmptyState>
        <EmptyState.Header>
          <EmptyState.FeaturedIcon icon={BookOpen01} />
        </EmptyState.Header>
        <EmptyState.Content>
          <EmptyState.Title as="h3">No report yet</EmptyState.Title>
          <EmptyState.Description>{sentence}</EmptyState.Description>
        </EmptyState.Content>
        <EmptyState.Footer>
          <ButtonLink href={LIBRARY_HOME} color="secondary">
            Back to the library
          </ButtonLink>
          <ButtonLink href={RUN_START}>Start a run</ButtonLink>
        </EmptyState.Footer>
      </EmptyState>
    </div>
  );
}

function Feed({ issuer, latest }: { issuer: Issuer; latest: string }) {
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-2.5">
        <Link
          href={LIBRARY_HOME}
          className={`${TEXT_LINK} w-fit text-small text-text-tertiary underline`}
        >
          Library
        </Link>
        <PageHeader
          as={ISSUER_HEADING}
          title={issuer.name}
          actions={
            <>
              <ButtonLink href={overviewHref(issuer.id, latest)} color="secondary">
                Open latest report
              </ButtonLink>
              <ButtonLink href={RUN_START}>New run</ButtonLink>
            </>
          }
        />
        <p className="text-body text-text-tertiary">{issuer.history.subtitle}</p>
      </div>
      <RunFeed issuer={issuer.id} history={issuer.history} />
    </div>
  );
}

/** An issuer's runs, newest first; an issuer with nothing to read gets the "No report yet" state. */
export function History({ issuer: id }: { issuer: string | undefined }) {
  return (
    <LibraryPage>
      {({ issuers }) => {
        const issuer = issuers.find((item) => item.id === id);
        if (issuer === undefined) return <Missing />;
        const { latest, empty } = issuer.history;
        if (empty !== null) return <NoReport issuer={issuer} sentence={empty} />;
        if (latest === null)
          throw new RangeError(`${issuer.id} has neither a latest run nor a sentence`);
        return <Feed issuer={issuer} latest={latest} />;
      }}
    </LibraryPage>
  );
}
