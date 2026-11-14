// The Share to group dialog (mock frame "Share to group", behaviour list 2.6; mock departure 18): a
// form modal, never the warning style. Nothing is written: a successful Share only tells the page it
// happened, and the page says so as sample data. The mock's Select wins over the predecessor's radios.
import { useEffect, useRef, useState, type SyntheticEvent } from "react";
import { Share07 } from "@untitledui/icons";
import { Dialog, Modal, ModalOverlay } from "@/components/application/modals/modal";
import { Button } from "@/components/base/buttons/button";
import { CloseButton } from "@/components/base/buttons/close-button";
import { Select } from "@/components/base/select/select";
import { TextArea } from "./parts/TextArea";

const TITLE_ID = "signal-share-title";

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
  headline: string;
  groups: { id: string; name: string }[];
  /** Share was pressed with a group chosen; the page says it was not written. */
  onShare: () => void;
  onCancel: () => void;
  /** Where focus goes once the dialog has gone: the control that opened it. */
  onGone: () => void;
};

const HINT = "The story starts a thread in this group, or joins the thread it already has there.";
const NO_GROUP = "Choose a group to share this story to.";

function ShareForm({ headline, groups, onShare, onCancel, onGone }: Props) {
  useOnGone(onGone);
  const [group, setGroup] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const submit = (event: SyntheticEvent) => {
    event.preventDefault();
    if (group === null) setError(true);
    else onShare();
  };
  return (
    <form noValidate onSubmit={submit} className="flex flex-col">
      {/* In the dialog's close slot: it closes through the overlay, which calls onCancel. */}
      <CloseButton label="Close" className="absolute top-3 right-3" />
      <div className="flex flex-col gap-4 p-6 pr-14">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-ds-md bg-surface-card text-text-secondary shadow-1 ring-1 ring-border-subtle ring-inset">
          <Share07 aria-hidden="true" className="size-5" />
        </span>
        <div className="flex min-w-0 flex-col gap-1">
          <h2 id={TITLE_ID} className="font-display text-h3 text-text-primary">
            Share to a group
          </h2>
          <p className="text-small text-text-secondary">{headline}</p>
        </div>
      </div>
      <div className="flex flex-col gap-5 px-6 pb-6">
        {groups.length === 0 ? (
          <p className="text-text-secondary">
            There are no groups yet. Create one to share this story.
          </p>
        ) : (
          <>
            <Select
              label="Group"
              placeholder="Choose a group"
              items={groups.map((g) => ({ id: g.id, label: g.name }))}
              value={group}
              isInvalid={error}
              hint={error ? NO_GROUP : HINT}
              onChange={(key) => {
                setGroup(key === null ? null : String(key));
                setError(false);
              }}
            >
              {(item) => <Select.Item id={item.id} label={item.label} />}
            </Select>
            <TextArea
              label="Note (optional)"
              hint="Plain text. Members see it as your first comment."
              maxLength={4000}
              rows={3}
            />
          </>
        )}
      </div>
      <div className="flex gap-3 px-6 pb-6 *:flex-1">
        <Button color="secondary" onPress={onCancel}>
          Cancel
        </Button>
        {groups.length === 0 ? null : (
          <Button color="primary" type="submit">
            Share
          </Button>
        )}
      </div>
    </form>
  );
}

export function ShareDialog({ open, ...form }: Props & { open: boolean }) {
  return (
    <ModalOverlay
      isOpen={open}
      isDismissable
      onOpenChange={(next) => {
        if (!next) form.onCancel();
      }}
    >
      <Modal className="sm:max-w-160">
        <Dialog aria-labelledby={TITLE_ID}>
          <ShareForm {...form} />
        </Dialog>
      </Modal>
    </ModalOverlay>
  );
}
