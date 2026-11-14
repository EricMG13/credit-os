import type { ReactNode } from "react";
import { useSource } from "../../source";
import { readSlice } from "../read";
import type { LibrarySlice } from "../slice";
import { PageTitle } from "./PageTitle";

/**
 * Every library route is full bleed, so this is the one wrapper that gives a page the shell's
 * padding (`p-8`), and the fallback states draw the page's own h1: `title` is the page name.
 */
function Padded({ children }: { children: ReactNode }) {
  return <div className="p-8">{children}</div>;
}

function Notice({ title, children }: { title: string; children: string }) {
  return (
    <Padded>
      <PageTitle>{title}</PageTitle>
      <p className="mt-6 text-text-secondary">{children}</p>
    </Padded>
  );
}

/**
 * Reads the library slice and draws `children` only from what the reader returned. App already
 * shows an invalid slice in place of the page; this keeps a page honest when rendered on its own.
 */
export function LibraryPage({
  title,
  children,
}: {
  title: string;
  children: (slice: LibrarySlice) => ReactNode;
}) {
  const result = readSlice(useSource().library);
  switch (result.kind) {
    case "absent":
      return <Notice title={title}>This data file holds no library pages</Notice>;
    case "invalid":
      return (
        <Notice title={title}>{`The library data has a malformed record: ${result.reason}`}</Notice>
      );
    case "ok":
      return <Padded>{children(result.data)}</Padded>;
  }
}
