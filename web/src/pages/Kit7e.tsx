import { Button } from "@/components/base/buttons/button";
import { AlertTriangle } from "@untitledui/icons";
import { Dialog, DialogTrigger, Modal, ModalOverlay } from "@/components/application/modals/modal";
import { SlideoutMenu } from "@/components/application/slideout-menus/slideout-menu";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { Input } from "@/components/base/input/input";
import { Card } from "@/components/card/Card";
import { ProgressSteps } from "@/components/steps/ProgressSteps";

function Heading({ id, children }: { id: string; children: string }) {
  return (
    <h2 id={id} className="font-display text-h2 text-text-primary">
      {children}
    </h2>
  );
}

/** The kit's drawer, modal and progress steps sections. */
export function KitOverlays() {
  return (
    <>
      <section aria-labelledby="kit-drawer" className="mt-8 flex flex-col gap-4">
        <Heading id="kit-drawer">Drawer</Heading>
        <div>
          <SlideoutMenu.Trigger>
            <Button color="secondary">Open drawer</Button>
            <SlideoutMenu isDismissable aria-labelledby="kit-drawer-title">
              {({ close }) => (
                <>
                  <SlideoutMenu.Header onClose={close}>
                    <h3 id="kit-drawer-title" className="font-display text-h3 text-text-primary">
                      Source detail
                    </h3>
                  </SlideoutMenu.Header>
                  <SlideoutMenu.Content>
                    <p className="text-body text-text-primary">
                      The body scrolls while the header and footer stay in place.
                    </p>
                    {Array.from({ length: 12 }, (_, i) => (
                      <p key={i} className="text-body text-text-secondary">
                        {`Sample paragraph ${String(i + 1)}: a passage the reader checks without leaving the page.`}
                      </p>
                    ))}
                  </SlideoutMenu.Content>
                  <SlideoutMenu.Footer className="flex justify-end gap-3">
                    <Button color="secondary" onPress={close}>
                      Done
                    </Button>
                  </SlideoutMenu.Footer>
                </>
              )}
            </SlideoutMenu>
          </SlideoutMenu.Trigger>
        </div>
      </section>

      <section aria-labelledby="kit-modal" className="mt-8 flex flex-col gap-4">
        <Heading id="kit-modal">Modal</Heading>
        <div className="flex flex-wrap items-center gap-3">
          <DialogTrigger>
            <Button color="primary">Start run</Button>
            <ModalOverlay isDismissable>
              <Modal className="sm:max-w-100">
                <Dialog aria-labelledby="kit-paid-run-title">
                  {({ close }) => (
                    <div className="flex flex-col gap-5 p-6">
                      <FeaturedIcon icon={AlertTriangle} color="warning" size="lg" />
                      <div className="flex flex-col gap-1">
                        <h3
                          id="kit-paid-run-title"
                          className="font-display text-h3 text-text-primary"
                        >
                          Start a paid run
                        </h3>
                        <p className="text-small text-text-secondary">
                          This run costs money and cannot be undone. It stops at the cap of USD 20.
                        </p>
                      </div>
                      <div className="flex gap-3">
                        <Button color="secondary" className="flex-1" onPress={close}>
                          Cancel
                        </Button>
                        <Button color="primary" className="flex-1" onPress={close}>
                          Start the run
                        </Button>
                      </div>
                    </div>
                  )}
                </Dialog>
              </Modal>
            </ModalOverlay>
          </DialogTrigger>

          <DialogTrigger>
            <Button color="secondary">Rename issuer</Button>
            <ModalOverlay isDismissable>
              <Modal className="sm:max-w-100">
                <Dialog aria-labelledby="kit-rename-title">
                  {({ close }) => (
                    <div className="flex flex-col gap-5 p-6">
                      <h3 id="kit-rename-title" className="font-display text-h3 text-text-primary">
                        Display name
                      </h3>
                      <Input label="Display name" placeholder="Issuer" />
                      <div className="flex justify-end gap-3">
                        <Button color="secondary" onPress={close}>
                          Cancel
                        </Button>
                        <Button color="primary" onPress={close}>
                          Save
                        </Button>
                      </div>
                    </div>
                  )}
                </Dialog>
              </Modal>
            </ModalOverlay>
          </DialogTrigger>
        </div>
      </section>

      <section aria-labelledby="kit-steps" className="mt-8 flex flex-col gap-4">
        <Heading id="kit-steps">Progress steps</Heading>
        <div className="max-w-2xl">
          <Card>
            <ProgressSteps
              steps={[
                { title: "Sources", state: "complete" },
                { title: "Capital structure", state: "complete" },
                { title: "Liquidity", state: "current" },
                { title: "Covenants", state: "incomplete" },
              ]}
            />
          </Card>
        </div>
      </section>
    </>
  );
}
