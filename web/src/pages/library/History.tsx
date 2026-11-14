import { Link } from "react-aria-components";
import { BookOpen01 } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { PageHeader } from "@/shell/PageHeader";
import { Button } from "@/components/base/buttons/button";
import { LibraryPage } from "./parts/LibraryPage";
import { NotHeld } from "./parts/NotHeld";
import { PAGE_NAME } from "./parts/PageTitle";
import { RunFeed } from "./parts/RunFeed";
import { ISSUER_HEADING, SECTION_HEADING } from "./parts/heading";
import { LIBRARY_HOME, RUN_START, TEXT_LINK, overviewHref } from "./parts/links";
import type { Issuer } from "./slice";

function NoReport({ issuer, sentence }: { issuer: Issuer; sentence: string }) {
  const Title = SECTION_HEADING;
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
          <EmptyState.Title as={Title}>No report yet</EmptyState.Title>
          <EmptyState.Description>{sentence}</EmptyState.Description>
        </EmptyState.Content>
        <EmptyState.Footer>
          <Button href={LIBRARY_HOME} color="secondary">
            Back to the library
          </Button>
          <Button href={RUN_START}>Start a run</Button>
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
              <Button href={overviewHref(issuer.id, latest)} color="secondary">
                Open latest report
              </Button>
              <Button href={RUN_START}>New run</Button>
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
    <LibraryPage title={PAGE_NAME.history}>
      {({ issuers }) => {
        const issuer = issuers.find((item) => item.id === id);
        if (issuer === undefined) {
          return (
            <NotHeld
              page={PAGE_NAME.history}
              title="No such issuer"
              description="The library holds no issuer at this address."
            />
          );
        }
        const { latest, empty } = issuer.history;
        if (empty !== null) return <NoReport issuer={issuer} sentence={empty} />;
        if (latest === null)
          throw new RangeError(`${issuer.id} has neither a latest run nor a sentence`);
        return <Feed issuer={issuer} latest={latest} />;
      }}
    </LibraryPage>
  );
}
