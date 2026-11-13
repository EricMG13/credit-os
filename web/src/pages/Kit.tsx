import type { ReactNode } from "react";
import type { IconProps } from "@/utils/is-react-component";
import { Button, styles } from "@/components/base/buttons/button";

function label(slug: string): string {
  const words = slug.replace("-", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function Plus({ className, "data-icon": slot }: IconProps) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      aria-hidden="true"
      data-icon={slot}
      className={className}
    >
      <path d="M10 4v12M4 10h12" />
    </svg>
  );
}

function Row({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap items-center gap-4">{children}</div>;
}

export function Kit() {
  const colours = Object.keys(styles.colors) as (keyof typeof styles.colors)[];
  const sizes = Object.keys(styles.sizes) as (keyof typeof styles.sizes)[];
  return (
    <main className="min-h-screen bg-surface-canvas p-8 text-text-primary">
      <h1 className="font-display text-h1 text-text-primary">Component kit</h1>

      <section className="mt-8 flex flex-col gap-4">
        <h2 className="font-display text-h2 text-text-primary">Button</h2>
        <Row>
          {colours.map((colour) => (
            <Button key={colour} color={colour} size="md">
              {label(colour)}
            </Button>
          ))}
        </Row>
        <Row>
          {sizes.map((size) => (
            <Button key={size} size={size}>
              {`Size ${size}`}
            </Button>
          ))}
        </Row>
        <Row>
          <Button isDisabled>Disabled</Button>
          <Button isLoading>Loading</Button>
          <Button iconLeading={Plus}>Leading icon</Button>
          <Button iconTrailing={Plus}>Trailing icon</Button>
        </Row>
      </section>
    </main>
  );
}
