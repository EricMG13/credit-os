const MARKS = {
  // The mock's chevron (ds.css .chev, .chev-u) and its arrow (.arrow), drawn from borders.
  down: "mx-1 mb-[3px] inline-block size-2 flex-none rotate-45 border-r-[1.5px] border-b-[1.5px] border-current",
  up: "mx-1 mt-[3px] inline-block size-2 flex-none -rotate-135 border-r-[1.5px] border-b-[1.5px] border-current",
  flat: "relative mx-1 inline-block h-[1.5px] w-3.5 flex-none bg-current after:absolute after:-top-[3px] after:right-0 after:size-1.5 after:rotate-45 after:border-t-[1.5px] after:border-r-[1.5px] after:border-current after:content-['']",
} as const;

/** The delivered direction as the mock's mark; hidden from a screen reader, which reads the delivered words beside it. */
export function DirectionMark({ direction }: { direction: keyof typeof MARKS }) {
  return <span aria-hidden="true" data-direction={direction} className={MARKS[direction]} />;
}
