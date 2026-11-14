/** A text link with the kit's visible focus ring (the shell draws none on a link). */
export function TextLink({ href, children }: { href: string; children: string }) {
  return (
    <a
      href={href}
      className="rounded-xs text-sm text-text-link underline focus-visible:outline-2 focus-visible:outline-solid focus-visible:outline-offset-2 focus-visible:outline-focus"
    >
      {children}
    </a>
  );
}
