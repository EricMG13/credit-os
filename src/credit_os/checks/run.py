"""`check_handoff` runs the checks that apply to a parsed handoff and returns their findings.

Later pull requests add steps here; each step is one plain line of this function.
"""

from credit_os.checks import structure
from credit_os.checks.findings import CheckContext, Finding, ordered
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.errors import HandoffError
from credit_os.handoff.reader import read_reader


def check_handoff(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    try:
        reader = read_reader(document)
    except HandoffError:
        return ordered(
            (
                *structure.check_reader(document, context),
                *structure.check_fence(document, context),
                *structure.check_register_id(document, context),
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
        )
    )
