"""3A PR 9a-2b: the context's value rules for deal terms, quotes, ratings and valuation (D24)."""

import orchestrator_context_rules_b_key as key
import pytest

from credit_os.orchestrator.context import ContextRefused, load_context


@pytest.mark.parametrize(("data", "problems"), list(key.RULES_B.values()), ids=list(key.RULES_B))
def test_d24_value_rules_b_give_the_keys_problems_in_order(
    data: bytes, problems: tuple[str, ...]
) -> None:
    if not problems:
        load_context(data)
        return
    with pytest.raises(ContextRefused) as caught:
        load_context(data)
    assert caught.value.problems == problems
