import { BookOpen01 } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { ButtonLink } from "./ButtonLink";
import { LIBRARY_HOME } from "./links";

/** A page's own "the library holds no such issuer, run or module" state, with the way back. */
export function NotHeld({ title, description }: { title: string; description: string }) {
  return (
    <EmptyState>
      <EmptyState.Header>
        <EmptyState.FeaturedIcon icon={BookOpen01} />
      </EmptyState.Header>
      <EmptyState.Content>
        <EmptyState.Title>{title}</EmptyState.Title>
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
