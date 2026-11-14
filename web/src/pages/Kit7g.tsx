import { ArrowLeft } from "@untitledui/icons";
import { Button } from "@/components/base/buttons/button";

/** The kit's link button section: an anchor with the button's look, in its states. */
export function KitLinkButton() {
  return (
    <section aria-labelledby="kit-link-button" className="mt-8 flex flex-col gap-4">
      <h2 id="kit-link-button" className="font-display text-h2 text-text-primary">
        Link button
      </h2>
      <div className="flex flex-wrap items-center gap-3">
        <Button href="#/library">Open the library</Button>
        <Button href="#/library" color="secondary" iconLeading={ArrowLeft}>
          Back to the library
        </Button>
        <Button href="#/library" isDisabled>
          Library unavailable
        </Button>
      </div>
    </section>
  );
}
