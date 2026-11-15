import type { ReactNode } from "react";
import { SearchLg } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { RegisterCard, RegisterTable } from "./RegisterTable";
import { SUBSECTION_HEADING } from "./heading";

/** What an Evidence register shows when it holds no row: any warning above, then a titled empty state. */
export function EmptyRegister({
  unknown,
  title,
  children,
}: {
  unknown: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4">
      {unknown}
      <EmptyState>
        <EmptyState.Header>
          <EmptyState.FeaturedIcon icon={SearchLg} />
        </EmptyState.Header>
        <EmptyState.Content>
          <EmptyState.Title as={SUBSECTION_HEADING}>{title}</EmptyState.Title>
          <EmptyState.Description>{children}</EmptyState.Description>
        </EmptyState.Content>
      </EmptyState>
    </div>
  );
}

/** An Evidence register page: any warning above, then its card, its table and the given header row. */
export function RegisterPage({
  unknown,
  title,
  count,
  description,
  head,
  children,
}: {
  unknown: ReactNode;
  title: string;
  count: string | null;
  description: string;
  head: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4">
      {unknown}
      <RegisterCard title={title} count={count} description={description}>
        <RegisterTable name={title} head={head}>
          {children}
        </RegisterTable>
      </RegisterCard>
    </div>
  );
}
