import pytest
from inspect_ai import eval

from lab_bench_2.lab_bench_2 import lab_bench_2


def test_unsupported_tag_raises() -> None:
    with pytest.raises(NotImplementedError):
        lab_bench_2(tag="seqqa2")


@pytest.mark.huggingface
@pytest.mark.dataset_download
def test_litqa3_bare_e2e() -> None:
    # given the litqa3 task under the default (bare) solver, with a mock grader
    # when
    [log] = eval(
        tasks=lab_bench_2(tag="litqa3"),
        model="mockllm/model",
        model_roles={"grader": "mockllm/model"},
        limit=1,
    )
    # then
    assert log.status == "success"
