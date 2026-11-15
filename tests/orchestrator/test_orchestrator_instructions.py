import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import orchestrator_instructions_key as key
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.orchestrator.calculate import CALCULATE
from credit_os.orchestrator.context import RunContext, load_context
from credit_os.orchestrator.instructions import (
    MAX_METHOD_BYTES,
    MODULE_TOOLS,
    SYSTEM_RULES,
    InstructionsRefused,
    first_request,
)
from credit_os.orchestrator.tools import SOURCE_TOOLS
from credit_os.orchestrator.write import MAX_DRAFT_BYTES, WRITE_TOOLS

HERE = Path(__file__).parent
CONTEXT: RunContext = load_context((HERE / "fixtures" / key.CONTEXT_FIXTURE).read_bytes())
METHOD_REASONS = {"method_empty", "method_size", "method_encoding", "method_marker"}


def _ids(rows: dict[str, object]) -> list[str]:
    return [name.replace(" ", "_") for name in rows]


def _build(module: str, method: bytes, handoffs: dict[str, bytes]) -> tuple[str, str]:
    request = first_request(
        module,
        method=method,
        context=CONTEXT,
        handoffs=handoffs,
        max_output_tokens=key.MAX_OUTPUT_TOKENS,
        effort=key.EFFORT,
    )
    system, user = request.messages
    return system.text, user.text


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_w1_main_row_matches_the_key_in_both_texts_and_digests() -> None:
    request = first_request(
        key.MODULE,
        method=key.METHOD,
        context=CONTEXT,
        handoffs=dict(key.HANDOFFS_GIVEN),
        max_output_tokens=key.MAX_OUTPUT_TOKENS,
        effort=key.EFFORT,
    )
    assert [m.role for m in request.messages] == ["system", "user"]
    system, user = request.messages[0].text, request.messages[1].text
    assert system == key.SYSTEM_TEXT
    assert user == key.USER_TEXT
    assert _sha(system) == key.SYSTEM_SHA256
    assert _sha(user) == key.USER_SHA256
    assert request.max_output_tokens == key.MAX_OUTPUT_TOKENS
    assert request.effort == key.EFFORT
    assert key.SYSTEM_RULES == SYSTEM_RULES


def test_d25_tools_are_the_six_in_order() -> None:
    request = first_request(
        key.MODULE,
        method=key.METHOD,
        context=CONTEXT,
        handoffs={},
        max_output_tokens=1,
        effort="e",
    )
    assert request.tools is MODULE_TOOLS
    assert tuple(t.name for t in MODULE_TOOLS) == key.TOOL_NAMES
    assert MODULE_TOOLS == (*SOURCE_TOOLS, CALCULATE, *WRITE_TOOLS)


def test_d1_a_module_without_producers_gets_an_empty_list() -> None:
    _, user = _build("CP-0", key.METHOD, {})
    assert user == key.USER_TEXT_NO_HANDOFFS


@pytest.mark.parametrize("consumer", list(key.ORDER), ids=list(key.ORDER))
def test_w1_handoffs_are_in_catalogue_order(consumer: str) -> None:
    given_order, expected = key.ORDER[consumer]
    handoffs = {module: key.HANDOFF_CP0 for module in given_order}
    _, user = _build(consumer, key.METHOD, handoffs)
    assert tuple(item["module"] for item in json.loads(user)["handoffs"]) == expected


_CHILD = """
import json, sys
sys.path.insert(0, sys.argv[1])
import orchestrator_instructions_key as key
from credit_os.orchestrator.catalogue import CATALOGUE
from credit_os.orchestrator.context import load_context
from credit_os.orchestrator.instructions import first_request
from credit_os.orchestrator.plan import producers
import hashlib

context = load_context(open(sys.argv[2], "rb").read())

def build(module, handoffs):
    return first_request(
        module, method=key.METHOD, context=context, handoffs=handoffs,
        max_output_tokens=key.MAX_OUTPUT_TOKENS, effort=key.EFFORT,
    )

main = build(key.MODULE, dict(key.HANDOFFS_GIVEN))
fan = set(producers(key.CATALOGUE_ORDER)["CP-5"])
five = build("CP-5", {m: key.HANDOFF_CP0 for m in fan})
sha = lambda text: hashlib.sha256(text.encode()).hexdigest()
print(json.dumps([
    sha(main.messages[0].text), sha(main.messages[1].text),
    [h["module"] for h in json.loads(five.messages[1].text)["handoffs"]],
]))
"""


@pytest.mark.parametrize("seed", key.SEEDS, ids=[f"seed_{s}" for s in key.SEEDS])
def test_w1_the_bytes_do_not_depend_on_the_hash_seed(seed: str) -> None:
    env = {**os.environ, "PYTHONHASHSEED": seed}
    args = [sys.executable, "-c", _CHILD, str(HERE), str(HERE / "fixtures" / key.CONTEXT_FIXTURE)]
    done = subprocess.run(args, check=True, capture_output=True, text=True, env=env)
    system_sha, user_sha, order = json.loads(done.stdout)
    assert (system_sha, user_sha) == (key.SYSTEM_SHA256, key.USER_SHA256)
    assert tuple(order) == key.FAN_IN


@pytest.mark.parametrize("text", list(key.ESCAPES), ids=[f"escape_{i}" for i in range(len(key.ESCAPES))])
def test_s6_a_handoff_text_is_escaped_as_the_key_says(text: str) -> None:
    _, user = _build(key.MODULE, key.METHOD, {"CP-1": text.encode("utf-8")})
    assert '"markdown":"' + key.ESCAPES[text] + '"' in user
    assert json.loads(user)["handoffs"][0]["markdown"] == text


@pytest.mark.parametrize("row", list(key.AT_BOUNDS), ids=_ids(key.AT_BOUNDS))
def test_d10_a_request_at_a_bound_is_built(row: str) -> None:
    module, method, handoffs = key.AT_BOUNDS[row]
    system, _ = _build(module, method, handoffs)
    opening = key.METHOD_OPEN.format(module=module, sha256=hashlib.sha256(method).hexdigest())
    assert system.startswith(key.SYSTEM_RULES + opening)
    assert system.endswith(key.METHOD_CLOSE)
    assert len(system) == len(key.SYSTEM_RULES + opening) + len(method.decode()) + len(key.METHOD_CLOSE)


@pytest.mark.parametrize("row", list(key.REFUSALS), ids=_ids(key.REFUSALS))
def test_d10_a_fault_is_refused_by_name_without_argument_text(row: str) -> None:
    reason, name, module, method, handoffs = key.REFUSALS[row]
    with pytest.raises(InstructionsRefused) as caught:
        _build(module, method, handoffs)
    assert caught.value.reason == reason
    assert caught.value.name == name
    assert str(caught.value) == f"instructions refused ({reason})"


def test_d10_the_caps_are_the_keys() -> None:
    assert MAX_METHOD_BYTES == key.MAX_METHOD_BYTES
    assert MAX_DRAFT_BYTES == key.MAX_HANDOFF_BYTES


def test_d10_the_first_fault_in_the_order_is_the_one_reported() -> None:
    with pytest.raises(InstructionsRefused) as caught:
        _build("CP-8", b"", {"CP-2": b""})
    assert caught.value.reason == "module"
    with pytest.raises(InstructionsRefused) as caught:
        _build(key.MODULE, b"", {"CP-2": b""})
    assert caught.value.reason == "method_empty"
    with pytest.raises(InstructionsRefused) as caught:
        _build(key.MODULE, key.METHOD, {"CP-2": b"", "CP-0": b""})
    assert (caught.value.reason, caught.value.name) == ("handoff_module", "CP-2")


@settings(max_examples=60, deadline=None)
@given(st.text(min_size=1, max_size=200))
def test_s4_any_handoff_text_loads_back_from_one_ascii_line(text: str) -> None:
    _, user = _build(key.MODULE, key.METHOD, {"CP-1": text.encode("utf-8")})
    assert user.isascii()
    assert "\n" not in user and "\r" not in user
    assert "<<<" not in user and ">>>" not in user
    assert json.loads(user) == {
        "module": key.MODULE,
        "run": key.RUN,
        "handoffs": [
            {"module": "CP-1", "sha256": hashlib.sha256(text.encode()).hexdigest(), "markdown": text}
        ],
    }


@settings(max_examples=80, deadline=None)
@given(st.binary(max_size=200))
def test_s2_any_method_is_refused_by_reason_or_sent_whole(method: bytes) -> None:
    try:
        system, _ = _build(key.MODULE, method, {})
    except InstructionsRefused as refused:
        assert refused.reason in METHOD_REASONS
        return
    text = method.decode("utf-8")
    frame = key.METHOD_OPEN.format(module=key.MODULE, sha256=hashlib.sha256(method).hexdigest())
    assert system == key.SYSTEM_RULES + frame + text + key.METHOD_CLOSE
    assert "<<<" not in text and ">>>" not in text
