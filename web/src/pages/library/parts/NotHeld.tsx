import { BookOpen01 } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { ButtonLink } from "./ButtonLink";
import { SECTION_HEADING } from "./heading";
import { PageTitle } from "./PageTitle";
import { LIBRARY_HOME } from "./links";

/** The state for a part of a page the library holds nothing at, with the way back. */
export function Absent({ title, description }: { title: string; description: string }) {
  return (
    <EmptyState>
      <EmptyState.Header>
        <EmptyState.FeaturedIcon icon={BookOpen01} />
      </EmptyState.Header>
      <EmptyState.Content>
        <EmptyState.Title as={SECTION_HEADING}>{title}</EmptyState.Title>
        <EmptyState.Description>{description}</EmptyState.Description>
      </EmptyState.Content>
      <EmptyState.Footer>
        <ButtonLink href={LIBRARY_HOME} color="secondary">
          Back to the library
        </ButtonLink>
      </EmptyState.Footer>
    </EmptyState>
  );
}

/** A page's own "the library holds no such issuer or run" state: the page name as the h1, then the state. */
export function NotHeld({
  page,
  title,
  description,
}: {
  page: string;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col gap-6">
      <PageTitle>{page}</PageTitle>
      <Absent title={title} description={description} />
    </div>
  );
}
