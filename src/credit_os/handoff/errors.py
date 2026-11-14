class HandoffError(ValueError):
    """A handoff Markdown file broke a parsing rule at a given line."""

    def __init__(self, line: int, message: str) -> None:
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.message = message


def echo(text: str) -> str:
    """Show at most 80 characters of text taken from the file, then an ellipsis."""
    return text if len(text) <= 80 else text[:80] + "\u2026"
