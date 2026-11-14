"""`check_handoff` runs the checks that apply to a parsed handoff and returns their findings.

Later pull requests add steps here; each step is one plain line of this function.
"""

from credit_os.checks import prose, structure
from credit_os.checks.findings import CheckContext, Finding, ordered
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.errors import HandoffError
from credit_os.handoff.reader import read_reader


def _prose_text(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    """The prose checks that need no reader view."""
    return (
        *prose.check_module_code(document, context),
        *prose.check_page(document, context),
        *prose.check_hash(document, context),
        *prose.check_bracket(document, context),
        *prose.check_pipeline_wording(document, context),
        *prose.check_provider_marker(document, context),
    )


def check_handoff(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    try:
        reader = read_reader(document)
    except HandoffError:
        return ordered(
            (
                *structure.check_reader(document, context),
                *structure.check_fence(document, context),
                *structure.check_register_id(document, context),
                *_prose_text(document, context),
            )
        )
    if reader.format == "earlier":
        return ordered(
            (
                *structure.check_format(document, context),
                *structure.check_reader_summary(document, context),
            )
        )
    return ordered(
        (
            *structure.check_passages(document, context),
            *structure.check_fence(document, context),
            *structure.check_register_id(document, context),
            *structure.check_registers(document, context),
            *prose.check_bottom_line(document, context),
            *prose.check_bottom_line_length(document, context),
            *_prose_text(document, context),
        )
    )
