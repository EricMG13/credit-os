// The name dialog (ruling 19, mock departure 18): a form modal that sets the display name in memory.
// Predecessor wording wins over the mock's ("Choose a display name", "Not now", "Save name").
import { useEffect, useRef, useState, type SyntheticEvent } from "react";
import { Dialog, Modal, ModalOverlay } from "@/components/application/modals/modal";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";

const TITLE_ID = "signal-name-title";

/** A display label, not a figure: the letters or digits that open the first two words, upper case. */
export function initialsOf(name: string): string {
  return name
    .split(/\s+/)
    .map((word) => /[\p{L}\p{N}]/u.exec(word)?.[0] ?? "")
    .filter((letter) => letter !== "")
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

/** Runs once when the dialog's content goes, after any exit animation, so focus never falls to the page. */
function useOnGone(then: () => void) {
  const latest = useRef(then);
  useEffect(() => {
    latest.current = then;
  });
  useEffect(
    () => () => {
      latest.current();
    },
    [],
  );
}

type Props = {
  /** The name now set; null on a first visit, when the dialog cannot be dismissed. */
  current: string | null;
  onSubmit: (name: string) => void;
  onCancel: () => void;
  /** Where focus goes once the dialog has gone: the name chip. */
  onGone: () => void;
};

/** The form is the dialog's content, so each opening starts from the current name with no error. */
function NameForm({ current, onSubmit, onCancel, onGone }: Props) {
  useOnGone(onGone);
  const [value, setValue] = useState(current ?? "");
  const [error, setError] = useState(false);
  const field = useRef<HTMLInputElement>(null);
  // On every opening focus starts in the field (the modal's own autofocus only runs on first mount).
  useEffect(() => {
    field.current?.focus();
  }, []);
  const submit = (event: SyntheticEvent) => {
    event.preventDefault();
    const name = value.trim();
    if (name === "") {
      setError(true);
      field.current?.focus();
      return;
    }
    onSubmit(name);
  };
  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-5 p-6">
      <div className="flex flex-col gap-1">
        <h2 id={TITLE_ID} className="font-display text-h3 text-text-primary">
          Your name
        </h2>
        <p className="text-small text-text-secondary">
          Signal shows your name next to what you save and follow. It is a display name, not a
          login.
        </p>
      </div>
      <Input
        ref={field}
        label="Display name"
        maxLength={60}
        value={value}
        isInvalid={error}
        hint={error ? "Enter a name to continue." : undefined}
        onChange={(next) => {
          setValue(next);
          setError(false);
        }}
      />
      <div className="flex justify-end gap-3">
        {current === null ? null : (
          <Button color="secondary" onPress={onCancel}>
            Cancel
          </Button>
        )}
        <Button color="primary" type="submit">
          Continue
        </Button>
      </div>
    </form>
  );
}

export function NameDialog({ open, ...form }: Props & { open: boolean }) {
  return (
    <ModalOverlay
      isOpen={open}
      isDismissable={false}
      isKeyboardDismissDisabled={form.current === null}
      onOpenChange={(next) => {
        if (!next) form.onCancel();
      }}
    >
      <Modal className="sm:max-w-160">
        <Dialog aria-labelledby={TITLE_ID}>
          <NameForm {...form} />
        </Dialog>
      </Modal>
    </ModalOverlay>
  );
}
