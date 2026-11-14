import { Heading } from "react-aria-components";
import { Lock01 } from "@untitledui/icons";
import { Button } from "@/components/base/buttons/button";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { Dialog, DialogTrigger, Modal, ModalOverlay } from "@/components/application/modals/modal";
import { StatusShape } from "@/components/status/shapes";
import type { StartDraft } from "../slice";
import { DetailsList } from "./DetailsList";

type Step = Extract<StartDraft, { step: "start" }>;

/** The Start step: the recap and what Submit does. Submit itself is the step action. */
export function Start({ recap, paid }: Pick<Step, "recap" | "paid">) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h2 className="font-display text-h3 text-text-primary">Start</h2>
        <p className="text-sm text-text-secondary">
          Everything is ready. This is the only step that spends money.
        </p>
      </div>
      <DetailsList rows={recap} />
      <div className="flex flex-col gap-1 border-t border-border-hairline pt-4">
        <h3 className="text-md font-semibold text-text-primary">Submit starts a paid run</h3>
        <p className="max-w-140 text-body text-text-secondary">{paid.text}</p>
      </div>
    </div>
  );
}

/** Submit and its one confirmation. Confirming only moves to the started snapshot: nothing is
 *  sent, stored or spent, because this page shows saved examples. */
export function Submit({ label, confirm }: { label: string; confirm: Step["confirm"] }) {
  return (
    <DialogTrigger>
      <Button size="xl" iconLeading={Lock01}>
        {label}
      </Button>
      <ModalOverlay isDismissable>
        <Modal className="max-w-100">
          <Dialog>
            {({ close }) => (
              <div className="flex flex-col gap-8 p-6">
                <div className="flex flex-col gap-4">
                  <FeaturedIcon
                    color="warning"
                    size="md"
                    icon={
                      <span className="flex size-4 [&>svg]:size-full">
                        <StatusShape shape="triangle" />
                      </span>
                    }
                  />
                  <div className="flex flex-col gap-0.5">
                    <Heading slot="title" className="text-md font-semibold text-text-primary">
                      {confirm.title}
                    </Heading>
                    <p className="text-sm text-text-tertiary">{confirm.text}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Button color="secondary" size="lg" onPress={close}>
                    Cancel
                  </Button>
                  <Button
                    size="lg"
                    onPress={() => {
                      window.location.hash = `#/run/start/${confirm.started}`;
                    }}
                  >
                    {confirm.action}
                  </Button>
                </div>
              </div>
            )}
          </Dialog>
        </Modal>
      </ModalOverlay>
    </DialogTrigger>
  );
}
