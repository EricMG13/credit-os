class HandoffError(ValueError):
    """A handoff Markdown file broke a parsing rule at a given line."""

    def __init__(self, line: int, message: str) -> None:
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.message = message
