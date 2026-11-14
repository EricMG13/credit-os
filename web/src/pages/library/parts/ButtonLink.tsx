import type { ReactNode } from "react";
import { Link } from "react-aria-components";
import { styles } from "@/components/base/buttons/button";
import { cx } from "@/utils/cx";

/** A link drawn as the kit's button: the kit's Button renders a `button`, and these go to a page. */
export function ButtonLink({
  href,
  color = "primary",
  children,
}: {
  href: string;
  color?: "primary" | "secondary";
  children: ReactNode;
}) {
  return (
    <Link
      href={href}
      className={cx(styles.common.root, styles.sizes.md.root, styles.colors[color].root)}
    >
      <span data-text className="px-0.5">
        {children}
      </span>
    </Link>
  );
}
