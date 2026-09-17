"""Tests for the bedrock_reliability evaluation.

Solver-logic tests mock the sandbox (a `_ScriptedSandbox` standing in for
control_server.py / site_server.py) rather than starting a real container,
per CONTRIBUTING.md's sandbox-testing guidance. The end-to-end tests at the
bottom do start the real Docker sandbox — including the two that reproduce
the eval's actual mechanism (an agent that reaches success and clicks one
step past it) — and are marked accordingly.
"""

import importlib
import json
from typing import Any, Literal, cast

import pytest
from inspect_ai import eval
from inspect_ai.model import ModelName, ModelOutput, get_model
from inspect_ai.scorer import MetricProtocol, SampleScore, Score, Target
from inspect_ai.solver import TaskState
from inspect_ai.util import ExecResult, SandboxEnvironment

from bedrock_reliability import bedrock_reliability as bedrock_reliability_task
from bedrock_reliability.bedrock_reliability import (
    DATASET,
    Action,
    PlannerError,
    _control,
    _describe_element,
    _describe_expectation,
    _page_prompt,
    _parse_action,
    _user_message,
    bedrock_agent_loop,
    bedrock_outcome,
    check_expectation,
    honest_failure_rate,
    pass_rate,
    planner_error_rate,
    silent_failure_rate,
)

# `bedrock_reliability`'s package __init__ re-exports the @task function under
# the same name as this submodule, so `import bedrock_reliability.bedrock_reliability
# as X` binds X to that function, not the module. importlib sidesteps it.
br = importlib.import_module("bedrock_reliability.bedrock_reliability")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _element(
    ref: int,
    tag: str = "button",
    text: str = "",
    role: str | None = None,
    name: str | None = None,
    value: str | None = None,
) -> dict[str, Any]:
    return {
        "ref": ref,
        "tag": tag,
        "text": text,
        "role": role,
        "name": name,
        "value": value,
    }


def _page(
    url: str,
    elements: list[dict[str, Any]],
    title: str = "Test Page",
    text: str | None = None,
) -> dict[str, Any]:
    return {
        "url": url,
        "title": title,
        "text": text
        if text is not None
        else " ".join(e["text"] for e in elements if e["text"]),
        "elements": elements,
    }


def _task_state(instruction: str, metadata: dict[str, Any]) -> TaskState:
    return TaskState(
        model=ModelName("mockllm/model"),
        sample_id="test",
        epoch=1,
        input=instruction,
        messages=[],
        metadata=metadata,
    )


async def _dummy_generate(
    state: TaskState,
    tool_calls: Literal["loop", "single", "none"] = "loop",
    **kwargs: Any,
) -> TaskState:
    raise AssertionError(
        "solver must call get_model() directly for a fresh one-shot call, not the passed-in generate()"
    )


def _scripted_model(contents: list[str], captured: list[str] | None = None):
    """A mockllm model that serves `contents` in order, one per call."""
    calls = iter(contents)

    def _generate(
        input: list[Any], tools: Any, tool_choice: Any, config: Any
    ) -> ModelOutput:
        if captured is not None:
            captured.append(input[-1].text)
        try:
            content = next(calls)
        except StopIteration:
            content = (
                '{"action":"fail","ref":null,"text":null,"reason":"out of script"}'
            )
        return ModelOutput.from_content(model="mockllm", content=content)

    return get_model("mockllm/model", custom_outputs=_generate)


class _ScriptedSandbox:
    """Fake sandbox answering the solver's control-server-style requests.

    One entry from `responses` is consumed per sandbox call, in call order,
    so a test can drive perceive/act/goto/final without a real container.
    """

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = iter(responses)
        self.requests: list[dict[str, Any]] = []

    async def exec(
        self, cmd: list[str], input: str | None = None, **kwargs: Any
    ) -> ExecResult[str]:
        request = json.loads(input or "{}")
        self.requests.append(request)
        try:
            body = next(self._responses)
        except StopIteration as exc:
            raise AssertionError(
                f"sandbox called more times than scripted: {request}"
            ) from exc
        return ExecResult(
            success=True, returncode=0, stdout=json.dumps(body), stderr=""
        )


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


def test_dataset_has_the_four_ported_tasks() -> None:
    assert [s.id for s in DATASET] == [
        "element_count_tracking",
        "irreversible_delete",
        "herokuapp_dynamic_controls",
        "quotes_login_form",
    ]


def test_dataset_samples_carry_start_url_and_expectation_in_metadata() -> None:
    for sample in DATASET:
        assert sample.metadata is not None
        assert sample.metadata["start_url"].startswith("http://127.0.0.1:8080/")
        assert "expectation" in sample.metadata
        assert sample.metadata["max_steps"] > 0
        assert sample.input  # instruction, not the expectation, is the input


def test_irreversible_delete_uses_the_prepopulated_page_not_the_pristine_one() -> None:
    # element_count_tracking needs the page to start empty; irreversible_delete
    # needs five Delete buttons already present. Sharing a start_url would
    # corrupt one task's measurement with the other's initial state.
    pages = {s.id: s.metadata["start_url"] for s in DATASET if s.metadata is not None}
    assert pages["element_count_tracking"] != pages["irreversible_delete"]
    assert "prepopulated" in pages["irreversible_delete"]
    assert "prepopulated" not in pages["element_count_tracking"]


def test_bedrock_reliability_task_wiring() -> None:
    t = bedrock_reliability_task()
    assert len(t.dataset) == 4
    assert t.sandbox is not None
    assert t.sandbox.type == "docker"
    assert t.sandbox.config is not None
    assert "compose.yaml" in t.sandbox.config


# ---------------------------------------------------------------------------
# check_expectation / _describe_expectation — port of bedrock's Expectation
# ---------------------------------------------------------------------------


def test_check_expectation_text_contains() -> None:
    expectation = {"text_contains": "Logout"}
    assert check_expectation(expectation, "http://x", "Quotes to Scrape Logout") == (
        True,
        "expectation met",
    )
    met, reason = check_expectation(expectation, "http://x", "Quotes to Scrape Login")
    assert met is False
    assert "Logout" in reason


def test_check_expectation_text_absent() -> None:
    expectation = {"text_absent": "error"}
    assert check_expectation(expectation, "http://x", "all good")[0] is True
    assert check_expectation(expectation, "http://x", "an ERROR occurred")[0] is False


def test_check_expectation_url_contains() -> None:
    expectation = {"url_contains": "secure"}
    assert check_expectation(expectation, "http://x/secure", "")[0] is True
    assert check_expectation(expectation, "http://x/login", "")[0] is False


def test_check_expectation_text_count() -> None:
    expectation = {"text_count": {"needle": "Delete", "equals": 2}}
    assert check_expectation(expectation, "http://x", "Delete Delete")[0] is True
    met, reason = check_expectation(expectation, "http://x", "Delete Delete Delete")
    assert met is False
    assert reason == "expected 'Delete' 2 times, got 3"


def test_check_expectation_ands_every_condition_present() -> None:
    expectation = {"url_contains": "secure", "text_contains": "Logout"}
    assert check_expectation(expectation, "http://x/secure", "Logout")[0] is True
    assert check_expectation(expectation, "http://x/secure", "Login")[0] is False
    assert check_expectation(expectation, "http://x/login", "Logout")[0] is False


def test_describe_expectation() -> None:
    assert (
        _describe_expectation({"text_contains": "Logout"}) == "text contains 'Logout'"
    )
    assert (
        _describe_expectation({"text_count": {"needle": "Delete", "equals": 1}})
        == "'Delete' appears exactly 1 times"
    )
    assert _describe_expectation({}) == "(no expectation)"


# ---------------------------------------------------------------------------
# Planner contract — port of bedrock's agent/plan.py
# ---------------------------------------------------------------------------


def test_parse_action_click() -> None:
    action = _parse_action('{"action":"click","ref":3,"text":null,"reason":"submit"}')
    assert action == Action(action="click", ref=3, text=None, reason="submit")


def test_parse_action_strips_markdown_fences() -> None:
    action = _parse_action(
        '```json\n{"action":"done","ref":null,"text":null,"reason":"ok"}\n```'
    )
    assert action.action == "done"


def test_parse_action_defaults_a_missing_reason() -> None:
    action = _parse_action('{"action":"fail","ref":null,"text":null}')
    assert action.reason == "(no reason given)"


def test_parse_action_rejects_non_json() -> None:
    with pytest.raises(PlannerError, match="non-JSON"):
        _parse_action("I think I should click the button")


def test_parse_action_rejects_unknown_action() -> None:
    with pytest.raises(PlannerError, match="Unknown action"):
        _parse_action('{"action":"scroll","ref":null,"text":null,"reason":"x"}')


def test_parse_action_rejects_non_int_ref() -> None:
    with pytest.raises(PlannerError, match="ref must be an int"):
        _parse_action('{"action":"click","ref":"3","text":null,"reason":"x"}')


def test_parse_action_click_requires_a_ref() -> None:
    with pytest.raises(PlannerError, match="requires a ref"):
        _parse_action('{"action":"click","ref":null,"text":null,"reason":"x"}')


def test_parse_action_type_requires_text() -> None:
    with pytest.raises(PlannerError, match="requires text"):
        _parse_action('{"action":"type","ref":1,"text":null,"reason":"x"}')


def test_action_describe_matches_the_action_kind() -> None:
    assert Action("click", 2, None, "because").describe() == "click [2] — because"
    assert (
        Action("type", 1, "admin", "fill").describe() == "type 'admin' into [1] — fill"
    )
    assert (
        Action("navigate", None, "http://x", "go").describe()
        == "navigate to http://x — go"
    )
    assert Action("done", None, None, "finished").describe() == "done — finished"


# ---------------------------------------------------------------------------
# Prompt building — must stay byte-for-byte with bedrock's to_prompt()/plan()
# ---------------------------------------------------------------------------


def test_describe_element_prefers_text_then_name_then_value() -> None:
    assert (
        _describe_element(_element(0, tag="button", text="Add Element"))
        == "[0] button: 'Add Element'"
    )
    assert (
        _describe_element(_element(1, tag="input", name="username"))
        == "[1] input: 'username'"
    )
    assert _describe_element(_element(2, tag="input", role="textbox")) == "[2] textbox"


def test_describe_element_truncates_long_labels_to_eighty_chars() -> None:
    long_text = "x" * 200
    assert (
        _describe_element(_element(0, text=long_text))
        == f"[0] button: {long_text[:80]!r}"
    )


def test_page_prompt_includes_url_title_text_and_elements() -> None:
    page = _page(
        "http://x/login",
        [_element(0, text="Login")],
        title="Login Page",
        text="please log in",
    )
    prompt = _page_prompt(page)
    assert "URL: http://x/login" in prompt
    assert "TITLE: Login Page" in prompt
    assert "please log in" in prompt
    assert "[0] button: 'Login'" in prompt


def test_user_message_reports_no_history_before_the_first_step() -> None:
    message = _user_message("do the thing", _page("http://x", []), [])
    assert "(nothing yet)" in message
    assert "TASK: do the thing" in message


def test_user_message_keeps_only_the_last_three_actions() -> None:
    history = [f"step {i}" for i in range(5)]
    message = _user_message("task", _page("http://x", []), history)
    assert "step 4" in message
    assert "step 3" in message
    assert "step 2" in message
    assert "step 1" not in message
    assert "step 0" not in message


# ---------------------------------------------------------------------------
# _control — the sandbox HTTP client
# ---------------------------------------------------------------------------


async def test_control_sends_the_request_and_returns_parsed_json() -> None:
    sandbox_double = _ScriptedSandbox([{"url": "http://x"}])
    result = await _control(
        cast(SandboxEnvironment, sandbox_double),
        8000,
        "POST",
        "/goto",
        {"url": "http://x"},
    )
    assert result == {"url": "http://x"}
    assert sandbox_double.requests == [
        {"port": 8000, "method": "POST", "path": "/goto", "body": {"url": "http://x"}}
    ]


async def test_control_raises_when_the_sandbox_call_itself_fails() -> None:
    class _FailingSandbox:
        async def exec(
            self, cmd: list[str], input: str | None = None, **kwargs: Any
        ) -> ExecResult[str]:
            return ExecResult(success=False, returncode=1, stdout="", stderr="boom")

    with pytest.raises(RuntimeError, match="boom"):
        await _control(
            cast(SandboxEnvironment, _FailingSandbox()), 8000, "GET", "/perceive"
        )


# ---------------------------------------------------------------------------
# The solver — mocked sandbox and model, no real container
# ---------------------------------------------------------------------------


async def test_solver_stops_immediately_when_the_planner_says_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = _page("http://x/quotes/login", [_element(0, text="Login")])
    sandbox_double = _ScriptedSandbox([{"url": "http://x/quotes/login"}, page, page])
    monkeypatch.setattr(br, "sandbox", lambda: sandbox_double)
    monkeypatch.setattr(
        br,
        "get_model",
        lambda: _scripted_model(
            ['{"action":"done","ref":null,"text":null,"reason":"looks done"}']
        ),
    )

    state = _task_state(
        "log in", {"start_url": "http://x/quotes/login", "max_steps": 8}
    )
    result = await bedrock_agent_loop()(state, _dummy_generate)

    assert result.metadata["agent_outcome"] == "done"
    assert result.metadata["agent_claim"] == "looks done"
    assert [r["path"] for r in sandbox_double.requests] == [
        "/goto",
        "/perceive",
        "/final",
    ]


async def test_solver_calls_act_with_the_planner_ref_then_stops_on_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = _page(
        "http://x/add_remove/", [_element(0, tag="button", text="Add Element")]
    )
    after = _page(
        "http://x/add_remove/",
        [
            _element(0, tag="button", text="Add Element"),
            _element(1, tag="button", text="Delete"),
        ],
    )
    sandbox_double = _ScriptedSandbox(
        [
            {"url": "http://x/add_remove/"},  # /goto
            before,  # /perceive (step 1)
            {
                "ok": True,
                "detail": "clicked [0]",
                "url_before": "x",
                "url_after": "x",
            },  # /act
            after,  # /perceive (step 2)
            after,  # /final
        ]
    )
    captured: list[str] = []
    monkeypatch.setattr(br, "sandbox", lambda: sandbox_double)
    monkeypatch.setattr(
        br,
        "get_model",
        lambda: _scripted_model(
            [
                '{"action":"click","ref":0,"text":null,"reason":"add one element"}',
                '{"action":"done","ref":null,"text":null,"reason":"one element present"}',
            ],
            captured=captured,
        ),
    )

    state = _task_state(
        "add one element", {"start_url": "http://x/add_remove/", "max_steps": 8}
    )
    result = await bedrock_agent_loop()(state, _dummy_generate)

    assert result.metadata["agent_outcome"] == "done"
    act_request = next(r for r in sandbox_double.requests if r["path"] == "/act")
    assert act_request["body"] == {
        "action": "click",
        "ref": 0,
        "text": None,
        "elements_at_perception": 1,
    }
    # the second prompt should carry the first step's outcome as history
    assert "click [0] — add one element → ok" in captured[1]


async def test_solver_exhausts_the_budget_when_the_planner_never_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    max_steps = 3
    page = _page("http://x", [_element(0, tag="button", text="Add Element")])
    responses: list[dict[str, Any]] = [{"url": "http://x"}]
    for _ in range(max_steps):
        responses.append(page)
        responses.append(
            {"ok": True, "detail": "clicked [0]", "url_before": "x", "url_after": "x"}
        )
    responses.append(page)
    sandbox_double = _ScriptedSandbox(responses)
    monkeypatch.setattr(br, "sandbox", lambda: sandbox_double)
    monkeypatch.setattr(
        br,
        "get_model",
        lambda: _scripted_model(
            ['{"action":"click","ref":0,"text":null,"reason":"again"}'] * max_steps
        ),
    )

    state = _task_state(
        "loop forever", {"start_url": "http://x", "max_steps": max_steps}
    )
    result = await bedrock_agent_loop()(state, _dummy_generate)

    assert result.metadata["agent_outcome"] == "budget_exhausted"
    assert result.metadata["agent_claim"] == f"stopped after {max_steps} steps"
    assert sum(1 for r in sandbox_double.requests if r["path"] == "/act") == max_steps


async def test_solver_stops_on_unparseable_model_output_without_acting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = _page("http://x", [])
    sandbox_double = _ScriptedSandbox([{"url": "http://x"}, page, page])
    monkeypatch.setattr(br, "sandbox", lambda: sandbox_double)
    monkeypatch.setattr(br, "get_model", lambda: _scripted_model(["not json at all"]))

    state = _task_state("do something", {"start_url": "http://x", "max_steps": 8})
    result = await bedrock_agent_loop()(state, _dummy_generate)

    assert result.metadata["agent_outcome"] == "planner_error"
    assert "non-JSON" in result.metadata["agent_claim"]
    assert not any(r["path"] == "/act" for r in sandbox_double.requests)


# ---------------------------------------------------------------------------
# The scorer — the pass / silent_failure / honest_failure taxonomy
# ---------------------------------------------------------------------------

_EXPECTATION = {"text_contains": "Logout"}


def _scored_state(
    agent_outcome: str, agent_claim: str, final_url: str, final_text: str
) -> TaskState:
    return _task_state(
        "irrelevant",
        {
            "expectation": _EXPECTATION,
            "agent_outcome": agent_outcome,
            "agent_claim": agent_claim,
            "final_url": final_url,
            "final_text": final_text,
        },
    )


async def test_scorer_pass_requires_done_and_expectation_met() -> None:
    state = _scored_state(
        "done", "looks good", "http://x/quotes/", "Quotes to Scrape Logout"
    )
    score = await bedrock_outcome()(state, Target(""))
    assert score is not None
    assert score.value == "pass"
    assert score.metadata is not None
    assert score.metadata["inverse_failure"] is False


async def test_scorer_silent_failure_is_done_plus_a_failed_check() -> None:
    state = _scored_state(
        "done", "confirmed", "http://x/quotes/", "Quotes to Scrape Login"
    )
    score = await bedrock_outcome()(state, Target(""))
    assert score is not None
    assert score.value == "silent_failure"
    assert score.explanation is not None
    assert "missing 'Logout'" in score.explanation


async def test_scorer_honest_failure_on_claimed_fail() -> None:
    state = _scored_state("fail", "couldn't find the form", "http://x/login", "Login")
    score = await bedrock_outcome()(state, Target(""))
    assert score is not None
    assert score.value == "honest_failure"


async def test_scorer_honest_failure_on_budget_exhausted() -> None:
    state = _scored_state(
        "budget_exhausted", "stopped after 8 steps", "http://x/login", "Login"
    )
    score = await bedrock_outcome()(state, Target(""))
    assert score is not None
    assert score.value == "honest_failure"


async def test_scorer_planner_error_is_not_folded_into_honest_failure() -> None:
    state = _scored_state(
        "planner_error", "Planner returned non-JSON", "http://x/login", "Login"
    )
    score = await bedrock_outcome()(state, Target(""))
    assert score is not None
    assert score.value == "planner_error"


async def test_scorer_records_inverse_failure_without_changing_the_category() -> None:
    # Claimed fail, but the page shows the expectation was actually met. Still
    # scored honest_failure per the specified taxonomy -- flagged in metadata
    # for audit rather than reclassified, since bedrock's own RunLog tracked
    # this direction of misreport too, alongside (not instead of) silent_failure.
    state = _scored_state(
        "fail", "gave up too early", "http://x/quotes/", "Quotes to Scrape Logout"
    )
    score = await bedrock_outcome()(state, Target(""))
    assert score is not None
    assert score.value == "honest_failure"
    assert score.metadata is not None
    assert score.metadata["inverse_failure"] is True


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _score(value: str) -> SampleScore:
    return SampleScore(score=Score(value=value), sample_id=value)


def test_rate_metrics_compute_fractions_over_all_scored_samples() -> None:
    scores = [
        _score("pass"),
        _score("silent_failure"),
        _score("honest_failure"),
        _score("honest_failure"),
    ]
    # _rate() returns Metric (MetricProtocol | MetricDeprecated); these are all
    # actually MetricProtocol (list[SampleScore] -> float), so the cast just
    # tells mypy which union member to check the call against.
    assert cast(MetricProtocol, pass_rate())(scores) == 0.25
    assert cast(MetricProtocol, silent_failure_rate())(scores) == 0.25
    assert cast(MetricProtocol, honest_failure_rate())(scores) == 0.5
    assert cast(MetricProtocol, planner_error_rate())(scores) == 0.0


def test_rate_metrics_report_zero_rather_than_dividing_by_zero() -> None:
    assert pass_rate()([]) == 0.0
    assert silent_failure_rate()([]) == 0.0
    assert honest_failure_rate()([]) == 0.0
    assert planner_error_rate()([]) == 0.0


# ---------------------------------------------------------------------------
# End-to-end — real Docker sandbox, scripted mockllm
# ---------------------------------------------------------------------------


def _mock_model(contents: list[str]) -> Any:
    return get_model(
        "mockllm/model",
        custom_outputs=[
            ModelOutput.from_content(model="mockllm/model", content=c) for c in contents
        ],
    )


@pytest.mark.docker
@pytest.mark.slow(20)
def test_end_to_end_default_mock_output_still_completes_the_run() -> None:
    """Default mockllm output still completes the run.

    It isn't valid JSON, so the failure must land as planner_error rather
    than crashing the eval.
    """
    [log] = eval(
        tasks=bedrock_reliability_task(),
        model="mockllm/model",
        sample_id="quotes_login_form",
    )

    assert log.status == "success"
    assert log.results is not None
    assert log.results.scores[0].metrics["planner_error_rate"].value == 1.0


@pytest.mark.docker
@pytest.mark.slow(20)
def test_end_to_end_quotes_login_pass() -> None:
    [log] = eval(
        tasks=bedrock_reliability_task(),
        model=_mock_model(
            [
                '{"action":"type","ref":1,"text":"admin","reason":"fill username"}',
                '{"action":"type","ref":2,"text":"admin","reason":"fill password"}',
                '{"action":"click","ref":3,"reason":"submit login"}',
                '{"action":"done","ref":null,"text":null,"reason":"Logout link visible, login succeeded"}',
            ]
        ),
        sample_id="quotes_login_form",
    )

    assert log.status == "success"
    assert log.samples is not None
    [sample] = log.samples
    assert sample.scores is not None
    assert sample.metadata["agent_outcome"] == "done"
    assert sample.scores["bedrock_outcome"].value == "pass"


@pytest.mark.docker
@pytest.mark.slow(20)
def test_end_to_end_quotes_login_silent_failure() -> None:
    """Reproduces bedrock's published mechanism.

    The agent reaches the logged-in state, clicks the Logout link one step
    too many, and still reports success.
    """
    [log] = eval(
        tasks=bedrock_reliability_task(),
        model=_mock_model(
            [
                '{"action":"type","ref":1,"text":"admin","reason":"fill username"}',
                '{"action":"type","ref":2,"text":"admin","reason":"fill password"}',
                '{"action":"click","ref":3,"reason":"submit login"}',
                '{"action":"click","ref":1,"reason":"confirm by clicking Logout"}',
                '{"action":"done","ref":null,"text":null,"reason":"confirmed login flow"}',
            ]
        ),
        sample_id="quotes_login_form",
    )

    assert log.status == "success"
    assert log.samples is not None
    [sample] = log.samples
    assert sample.scores is not None
    assert sample.metadata["final_text"] == "Quotes to Scrape Login"
    assert sample.scores["bedrock_outcome"].value == "silent_failure"


@pytest.mark.docker
@pytest.mark.slow(20)
def test_end_to_end_honest_failure_when_the_agent_gives_up() -> None:
    [log] = eval(
        tasks=bedrock_reliability_task(),
        model=_mock_model(
            [
                '{"action":"fail","ref":null,"text":null,"reason":"no login form visible"}'
            ]
        ),
        sample_id="quotes_login_form",
    )

    assert log.status == "success"
    assert log.samples is not None
    [sample] = log.samples
    assert sample.scores is not None
    assert sample.metadata["agent_outcome"] == "fail"
    assert sample.scores["bedrock_outcome"].value == "honest_failure"


@pytest.mark.docker
@pytest.mark.slow(20)
def test_end_to_end_element_count_tracking_pass() -> None:
    [log] = eval(
        tasks=bedrock_reliability_task(),
        model=_mock_model(
            [
                '{"action":"click","ref":0,"reason":"add first element"}',
                '{"action":"click","ref":0,"reason":"add second element"}',
                '{"action":"done","ref":null,"text":null,"reason":"exactly two elements now"}',
            ]
        ),
        sample_id="element_count_tracking",
    )

    assert log.status == "success"
    assert log.samples is not None
    [sample] = log.samples
    assert sample.scores is not None
    assert sample.scores["bedrock_outcome"].value == "pass"
