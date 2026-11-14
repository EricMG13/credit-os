import { styles } from "@/components/base/buttons/button";
import { cx } from "@/utils/cx";

const GREY = "text-text-tertiary hover:text-text-secondary hover:*:data-text:decoration-current";

/** The mock's `lnk` (brand, semibold, underlined on hover only) or, grey, its `lnk-g`; the kit's
 *  link styles carry the visible focus ring. */
export const textLinkClass = (grey = false) =>
  cx(
    styles.common.root,
    styles.colors["link-color"].root,
    styles.sizes.md.linkRoot,
    "font-semibold",
    grey && GREY,
  );

export function TextLink({
  href,
  children,
  grey = false,
}: {
  href: string;
  children: string;
  grey?: boolean;
}) {
  return (
    <a href={href} className={textLinkClass(grey)}>
      <span data-text>{children}</span>
    </a>
  );
}
