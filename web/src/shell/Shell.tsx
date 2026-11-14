import type { ReactNode } from "react";
import { BookOpen01, Cube01, Grid01, PlayCircle, Signal01 } from "@untitledui/icons";
import { NavButton } from "@/components/application/app-navigation/base-components/nav-button";

export type Area = "library" | "model" | "run" | "signal" | "kit";

const ITEMS = [
  { area: "library", label: "Library", href: "#/", icon: BookOpen01 },
  { area: "model", label: "Model", href: "#/model", icon: Cube01 },
  { area: "run", label: "Run", href: "#/run", icon: PlayCircle },
  { area: "signal", label: "Signal", href: "#/signal", icon: Signal01 },
  { area: "kit", label: "Kit", href: "#/kit", icon: Grid01 },
] as const;

/** The slim icon rail and the page region on the canvas. */
export function Shell({
  current,
  bleed = false,
  children,
}: {
  current: Area;
  bleed?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="flex h-screen bg-surface-canvas text-text-primary">
      <aside style={{ width: 68 }} className="flex h-full max-h-full max-w-full py-1 pl-1">
        <div className="flex w-auto flex-col rounded-xl bg-primary pt-5 ring-1 ring-secondary ring-inset">
          <div className="flex justify-center px-3">
            <img src="./symbol.svg" alt="" width="24" height="24" className="size-6" />
          </div>
          <nav aria-label="Areas">
            <ul className="mt-5 flex flex-col gap-0.5 px-3.5">
              {ITEMS.map((item) => (
                <li key={item.area}>
                  <NavButton
                    current={item.area === current}
                    href={item.href}
                    label={item.label}
                    icon={item.icon}
                  />
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </aside>
      <main className={`min-w-0 flex-1 overflow-y-auto${bleed ? "" : " p-8"}`}>{children}</main>
    </div>
  );
}
