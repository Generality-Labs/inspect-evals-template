import pytest

from lab_bench_2.dataset import (
    LAB_BENCH_2_DATASET_PATH,
    LAB_BENCH_2_DATASET_REVISION,
    record_to_sample,
)
from utils.huggingface import (
    DatasetInfosDict,
    assert_huggingface_dataset_structure,
    get_dataset_infos_dict,
)


class TestRecordToSample:
    def test_maps_core_fields(self) -> None:
        # given a litqa3-style record (synthetic, schema-faithful)
        record = {
            "id": "litqa3-0001",
            "tag": "litqa3",
            "type": "",
            "question": "What protein does the human SNCA gene encode?",
            "ideal": "Alpha-synuclein",
            "sources": ["https://example.org/paper"],
            "prompt_suffix": "",
        }

        # when
        sut = record_to_sample(record)

        # then
        assert sut.id == "litqa3-0001"
        assert sut.target == "Alpha-synuclein"
        assert "SNCA" in str(sut.input)
        assert sut.metadata is not None
        assert sut.metadata["tag"] == "litqa3"
        assert sut.metadata["sources"] == ["https://example.org/paper"]

    def test_appends_prompt_suffix(self) -> None:
        # given a record with a prompt suffix
        record = {
            "id": "litqa3-0002",
            "tag": "litqa3",
            "question": "What is the capital of France?",
            "ideal": "Paris",
            "prompt_suffix": "Answer concisely.",
        }

        # when
        sut = record_to_sample(record)

        # then
        assert str(sut.input).endswith("Answer concisely.")

    def test_defaults_when_optional_fields_missing(self) -> None:
        # given a record without optional fields
        record = {
            "id": "litqa3-0003",
            "question": "Q?",
            "ideal": "A",
        }

        # when
        sut = record_to_sample(record)

        # then
        assert sut.metadata is not None
        assert sut.metadata["sources"] == []
        assert sut.metadata["type"] is None


@pytest.fixture(scope="module")
def dataset_infos() -> DatasetInfosDict:
    return get_dataset_infos_dict(
        LAB_BENCH_2_DATASET_PATH, revision=LAB_BENCH_2_DATASET_REVISION
    )


@pytest.mark.huggingface
@pytest.mark.dataset_download
def test_litqa3_dataset_structure(dataset_infos: DatasetInfosDict) -> None:
    assert_huggingface_dataset_structure(
        dataset_infos,
        {
            "configs": {
                "litqa3": {
                    "splits": ["train"],
                    "features": {
                        "id": "string",
                        "question": "string",
                        "ideal": "string",
                        "tag": "string",
                    },
                }
            }
        },
    )
