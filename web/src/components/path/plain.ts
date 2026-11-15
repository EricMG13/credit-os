/** The characters a file path uses; a `%` only starts a two-digit escape. */
const SEGMENT = /^(?:[A-Za-z0-9._~@+=,-]|%[0-9A-Fa-f]{2})+$/;

/** Plain: allow-listed, and neither `.`, `..` nor a slash once percent-decoded. */
export function plainSegment(segment: string): boolean {
  if (!SEGMENT.test(segment)) return false;
  try {
    const decoded = decodeURIComponent(segment);
    return decoded !== "." && decoded !== ".." && !/[/\\]/.test(decoded);
  } catch (error) {
    if (!(error instanceof URIError)) throw error;
    return false; // an escape that is not UTF-8 is refused like any other odd path
  }
}
