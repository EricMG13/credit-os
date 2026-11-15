/** The characters a file path uses; a `%` only starts a two-digit escape. */
const SEGMENT = /^(?:[A-Za-z0-9._~@+=,-]|%[0-9A-Fa-f]{2})+$/;

// C0 controls (U+0000-U+001F) and DEL: an escape for one is not a path a file has.
const CONTROL = /[\u0000-\u001F\u007F]/;

/** Plain: allow-listed, and neither `.`, `..`, a slash nor a control character once percent-decoded. */
export function plainSegment(segment: string): boolean {
  if (!SEGMENT.test(segment)) return false;
  try {
    const decoded = decodeURIComponent(segment);
    return decoded !== "." && decoded !== ".." && !/[/\\]/.test(decoded) && !CONTROL.test(decoded);
  } catch (error) {
    if (!(error instanceof URIError)) throw error;
    return false; // an escape that is not UTF-8 is refused like any other odd path
  }
}
