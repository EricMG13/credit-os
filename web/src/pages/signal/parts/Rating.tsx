// After the shadcnblocks rating: three marks and a word, read-only. `marks` is how many are filled;
// the word is supplied. The name read aloud is the word and "signal": no number is computed.
import { Star01 } from "@untitledui/icons";
import { cx } from "@/utils/cx";

export function Rating({ marks, word }: { marks: 1 | 2 | 3; word: string }) {
  return (
    <span
      role="img"
      aria-label={`${word} signal`}
      className="inline-flex items-center gap-2 text-sm font-semibold text-text-primary"
    >
      <span className="flex gap-1" aria-hidden="true">
        {[1, 2, 3].map((position) => (
          <Star01
            key={position}
            className={cx("size-4", position <= marks ? "fill-current" : "text-fg-quaternary")}
          />
        ))}
      </span>
      <span aria-hidden="true">{word}</span>
    </span>
  );
}
