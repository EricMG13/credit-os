/** A run's address in the library, without a page: `#/model/<issuer>/<run>`, each id encoded. */
export function runAddress(issuer: string, run: string): string {
  return `#/model/${encodeURIComponent(issuer)}/${encodeURIComponent(run)}`;
}
