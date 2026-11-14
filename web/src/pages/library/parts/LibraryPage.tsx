import type { ReactNode } from "react";
import { useSource } from "../../source";
import { readSlice } from "../read";
import type { LibrarySlice } from "../slice";

/**
 * Reads the library slice and draws `children` only from what the reader returned. App already
 * shows an invalid slice in place of the page; this keeps a page honest when rendered on its own.
 */
export function LibraryPage({ children }: { children: (slice: LibrarySlice) => ReactNode }) {
  const result = readSlice(useSource().library);
  switch (result.kind) {
    case "absent":
      return <p className="text-text-secondary">Library data is missing</p>;
    case "invalid":
      return (
        <p className="text-text-secondary">
          The library data has a malformed record: {result.reason}
        </p>
      );
    case "ok":
      return <>{children(result.data)}</>;
  }
}
