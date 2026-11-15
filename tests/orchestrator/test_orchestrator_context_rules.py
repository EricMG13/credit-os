"""3A PR 9a-2a: the context's value rules for the run, issuer, assumptions and questions (D24)."""

import orchestrator_context_rules_key as key
import pytest

from credit_os.orchestrator.context import ContextRefused, load_context


@pytest.mark.parametrize(("data", "problems"), list(key.RULES.values()), ids=list(key.RULES))
def test_d24_value_rules_give_the_keys_problems_in_order(
    data: bytes, problems: tuple[str, ...]
) -> None:
    if not problems:
        load_context(data)
        return
    with pytest.raises(ContextRefused) as caught:
        load_context(data)
    assert caught.value.problems == problems
