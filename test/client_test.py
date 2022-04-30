from dataclasses import dataclass
import json
import os
from unittest.mock import patch
import pytest
from eppo_client.client import EppoClient
from eppo_client.configuration_requestor import (
    ExperimentConfigurationDto,
    ExperimentConfigurationRequestor,
    VariationDto,
)
from eppo_client.shard import ShardRange

mock_api_key = "mock-api-key"


@dataclass
class AssignmentTestCase:
    experiment: str
    percentExposure: float
    variations: list[VariationDto]
    subjects: list[str]
    expectedAssignments: list[str]


test_data = []
for file_name in [file for file in os.listdir("test/test-data/assignment")]:
    with open("test/test-data/assignment/{}".format(file_name)) as test_case_json:
        test_case_dict = json.load(test_case_json)
        variations = [
            VariationDto.from_dict(variation_dict)
            for variation_dict in test_case_dict["variations"]
        ]
        test_case_dict["variations"] = variations
        test_data.append(AssignmentTestCase(**test_case_dict))


def test_assign_blank_experiment():
    client = EppoClient(config_requestor=ExperimentConfigurationRequestor())
    with pytest.raises(Exception) as exc_info:
        client.assign("subject-1", "")
    assert exc_info.value.args[0] == "Invalid value for flag: cannot be blank"


def test_assign_blank_subject():
    client = EppoClient(config_requestor=ExperimentConfigurationRequestor())
    with pytest.raises(Exception) as exc_info:
        client.assign("", "experiment-1")
    assert exc_info.value.args[0] == "Invalid value for subject: cannot be blank"


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_assign_subject_not_in_sample(mock_config_requestor):
    mock_config_requestor.get_configuration.return_value = ExperimentConfigurationDto(
        subjectShards=10000,
        percentExposure=0,
        enabled=True,
        variations=[
            VariationDto(name="control", shardRange=ShardRange(start=0, end=100))
        ],
        name="recommendation_algo",
    )
    client = EppoClient(config_requestor=mock_config_requestor)
    assert client.assign("user-1", "flag-1") is None


@pytest.mark.parametrize("test_case", test_data)
def test_assign_subject_in_sample(test_case):
    print("---- Test case for {} Experiment".format(test_case.experiment))
    with patch(
        "eppo_client.configuration_requestor.ExperimentConfigurationRequestor"
    ) as mock_config_requestor:
        mock_config_requestor.get_configuration.return_value = (
            ExperimentConfigurationDto(
                subjectShards=10000,
                percentExposure=test_case.percentExposure,
                enabled=True,
                variations=test_case.variations,
                name=test_case.experiment,
            )
        )
        client = EppoClient(config_requestor=mock_config_requestor)
        assignments = [
            client.assign(subject, test_case.experiment)
            for subject in test_case.subjects
        ]
        assert assignments == test_case.expectedAssignments
