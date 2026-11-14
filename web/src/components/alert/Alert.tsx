import type { ReactNode } from "react";
import { StatusShape, type Shape } from "@/components/status/shapes";

// Follows HyperUI Toasts: Success, Error, Warning, Info and "With action button" (Alert),
// and "Standout" (Callout).

type Tone = "success" | "warning" | "error" | "info";

// Each tone's own classes, written out whole so the class scan finds them.
const TONES: Record<
  Tone,
  { shape: Shape; box: string; mark: string; text: string; role: "alert" | "status" }
> = {
  success: {
    shape: "filled circle",
    box: "border-success-edge bg-success-fill",
    mark: "text-success-mark",
    text: "text-success-text",
    role: "status",
  },
  warning: {
    shape: "triangle",
    box: "border-warning-edge bg-warning-fill",
    mark: "text-warning-mark",
    text: "text-warning-text",
    role: "alert",
  },
  error: {
    shape: "diamond",
    box: "border-error-edge bg-error-fill",
    mark: "text-error-mark",
    text: "text-error-text",
    role: "alert",
  },
  info: {
    shape: "ring",
    box: "border-info-edge bg-info-fill",
    mark: "text-info-mark",
    text: "text-info-text",
    role: "status",
  },
};

interface AlertProps {
  tone: Tone;
  title: string;
  children?: ReactNode;
  /** One action under the text; the alert has no dismiss button. */
  action?: ReactNode;
}

export function Alert({ tone, title, children, action }: AlertProps) {
  const t = TONES[tone];
  return (
    <div role={t.role} className={`rounded-md border p-4 shadow-sm ${t.box}`}>
      <div className="flex items-start gap-4">
        <span className={`-mt-0.5 flex size-6 items-center justify-center ${t.mark}`}>
          <StatusShape shape={t.shape} />
        </span>
        <div className="flex-1">
          <strong className={`block leading-tight font-medium ${t.text}`}>{title}</strong>
          {children ? <p className={`mt-0.5 text-sm ${t.text}`}>{children}</p> : null}
          {action ? <div className="mt-2">{action}</div> : null}
        </div>
      </div>
    </div>
  );
}

interface CalloutProps {
  title: string;
  children: ReactNode;
}

/** A static standout note in the info colours: the passage that says what would change the view. */
export function Callout({ title, children }: CalloutProps) {
  const t = TONES.info;
  return (
    <div role="note" className="border-s-4 border-info-mark bg-info-fill p-4">
      <div className={`flex items-center gap-2 ${t.mark}`}>
        <StatusShape shape={t.shape} />
        <strong className={`block leading-tight font-medium ${t.text}`}>{title}</strong>
      </div>
      <p className={`mt-1 text-body ${t.text}`}>{children}</p>
    </div>
  );
}
