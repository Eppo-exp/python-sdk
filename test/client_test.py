import json
import os
from time import sleep
from unittest.mock import patch
import httpretty  # type: ignore
import pytest
from eppo_client.assignment_logger import AssignmentLogger
from eppo_client.client import EppoClient
from eppo_client.config import Config
from eppo_client.configuration_requestor import (
    AllocationDto,
    ExperimentConfigurationDto,
    VariationDto,
)
from eppo_client.rules import Condition, OperatorType, Rule
from eppo_client.shard import ShardRange
from eppo_client import init, get_instance

test_data = []
for file_name in [file for file in os.listdir("test/test-data/assignment-v2")]:
    with open("test/test-data/assignment-v2/{}".format(file_name)) as test_case_json:
        test_case_dict = json.load(test_case_json)
        test_data.append(test_case_dict)

MOCK_BASE_URL = "http://localhost:4001/api"


@pytest.fixture(scope="session", autouse=True)
def init_fixture():
    httpretty.enable()
    with open("test/test-data/rac-experiments-v3.json") as mock_rac_response:
        httpretty.register_uri(
            httpretty.GET,
            MOCK_BASE_URL + "/randomized_assignment/v3/config",
            body=json.dumps(json.load(mock_rac_response)),
        )
        client = init(
            Config(
                base_url=MOCK_BASE_URL,
                api_key="dummy",
                assignment_logger=AssignmentLogger(),
            )
        )
        sleep(0.1)  # wait for initialization
        yield
        client._shutdown()
        httpretty.disable()


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_assign_blank_experiment(mock_config_requestor):
    client = EppoClient(
        config_requestor=mock_config_requestor, assignment_logger=AssignmentLogger()
    )
    with pytest.raises(Exception) as exc_info:
        client.get_assignment("subject-1", "")
    assert exc_info.value.args[0] == "Invalid value for flag_key: cannot be blank"


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_assign_blank_subject(mock_config_requestor):
    client = EppoClient(
        config_requestor=mock_config_requestor, assignment_logger=AssignmentLogger()
    )
    with pytest.raises(Exception) as exc_info:
        client.get_assignment("", "experiment-1")
    assert exc_info.value.args[0] == "Invalid value for subject_key: cannot be blank"


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_assign_subject_not_in_sample(mock_config_requestor):
    allocation = AllocationDto(
        percent_exposure=0,
        variations=[
            VariationDto(
                name="control",
                value="control",
                shardRange=ShardRange(start=0, end=10000),
            )
        ],
    )
    mock_config_requestor.get_configuration.return_value = ExperimentConfigurationDto(
        subjectShards=10000,
        enabled=True,
        name="recommendation_algo",
        overrides=dict(),
        allocations={"allocation": allocation},
    )
    client = EppoClient(
        config_requestor=mock_config_requestor, assignment_logger=AssignmentLogger()
    )
    assert client.get_assignment("user-1", "experiment-key-1") is None


@patch("eppo_client.assignment_logger.AssignmentLogger")
@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_log_assignment(mock_config_requestor, mock_logger):
    allocation = AllocationDto(
        percent_exposure=1,
        variations=[
            VariationDto(
                name="control",
                value="control",
                shardRange=ShardRange(start=0, end=10000),
            )
        ],
    )
    mock_config_requestor.get_configuration.return_value = ExperimentConfigurationDto(
        allocations={"allocation": allocation},
        rules=[Rule(conditions=[], allocation_key="allocation")],
        subjectShards=10000,
        enabled=True,
        name="recommendation_algo",
        overrides=dict(),
    )
    client = EppoClient(
        config_requestor=mock_config_requestor, assignment_logger=mock_logger
    )
    assert client.get_assignment("user-1", "experiment-key-1") == "control"
    assert mock_logger.log_assignment.call_count == 1


@patch("eppo_client.assignment_logger.AssignmentLogger")
@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_get_assignment_handles_logging_exception(mock_config_requestor, mock_logger):
    allocation = AllocationDto(
        percent_exposure=1,
        variations=[
            VariationDto(
                name="control",
                value="control",
                shardRange=ShardRange(start=0, end=10000),
            )
        ],
    )
    mock_config_requestor.get_configuration.return_value = ExperimentConfigurationDto(
        subjectShards=10000,
        allocations={"allocation": allocation},
        enabled=True,
        rules=[Rule(conditions=[], allocation_key="allocation")],
        name="recommendation_algo",
        overrides=dict(),
    )
    mock_logger.log_assignment.side_effect = ValueError("logging error")
    client = EppoClient(
        config_requestor=mock_config_requestor, assignment_logger=mock_logger
    )
    assert client.get_assignment("user-1", "experiment-key-1") == "control"


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_assign_subject_with_with_attributes_and_rules(mock_config_requestor):
    allocation = AllocationDto(
        percent_exposure=1,
        variations=[
            VariationDto(
                name="control",
                value="control",
                shardRange=ShardRange(start=0, end=10000),
            )
        ],
    )
    matches_email_condition = Condition(
        operator=OperatorType.MATCHES, value=".*@eppo.com", attribute="email"
    )
    text_rule = Rule(conditions=[matches_email_condition], allocation_key="allocation")
    mock_config_requestor.get_configuration.return_value = ExperimentConfigurationDto(
        subjectShards=10000,
        allocations={"allocation": allocation},
        enabled=True,
        name="experiment-key-1",
        overrides=dict(),
        rules=[text_rule],
    )
    client = EppoClient(
        config_requestor=mock_config_requestor, assignment_logger=AssignmentLogger()
    )
    assert client.get_assignment("user-1", "experiment-key-1") is None
    assert (
        client.get_assignment(
            "user1", "experiment-key-1", {"email": "test@example.com"}
        )
        is None
    )
    assert (
        client.get_assignment("user1", "experiment-key-1", {"email": "test@eppo.com"})
        == "control"
    )


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_with_subject_in_overrides(mock_config_requestor):
    allocation = AllocationDto(
        percent_exposure=1,
        variations=[
            VariationDto(
                name="control",
                value="control",
                shardRange=ShardRange(start=0, end=10000),
            )
        ],
    )
    mock_config_requestor.get_configuration.return_value = ExperimentConfigurationDto(
        subjectShards=10000,
        allocations={"allocation": allocation},
        enabled=True,
        rules=[Rule(conditions=[], allocation_key="allocation")],
        name="recommendation_algo",
        overrides={"d6d7705392bc7af633328bea8c4c6904": "override-variation"},
        typedOverrides={"d6d7705392bc7af633328bea8c4c6904": "override-variation"},
    )
    client = EppoClient(
        config_requestor=mock_config_requestor, assignment_logger=AssignmentLogger()
    )
    assert client.get_assignment("user-1", "experiment-key-1") == "override-variation"


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_with_subject_in_overrides_exp_disabled(mock_config_requestor):
    allocation = AllocationDto(
        percent_exposure=0,
        variations=[
            VariationDto(
                name="control",
                value="control",
                shardRange=ShardRange(start=0, end=10000),
            )
        ],
    )
    mock_config_requestor.get_configuration.return_value = ExperimentConfigurationDto(
        subjectShards=10000,
        allocations={"allocation": allocation},
        enabled=False,
        rules=[Rule(conditions=[], allocation_key="allocation")],
        name="recommendation_algo",
        overrides={"d6d7705392bc7af633328bea8c4c6904": "override-variation"},
        typedOverrides={"d6d7705392bc7af633328bea8c4c6904": "override-variation"},
    )
    client = EppoClient(
        config_requestor=mock_config_requestor, assignment_logger=AssignmentLogger()
    )
    assert client.get_assignment("user-1", "experiment-key-1") == "override-variation"


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_with_null_experiment_config(mock_config_requestor):
    mock_config_requestor.get_configuration.return_value = None
    client = EppoClient(
        config_requestor=mock_config_requestor, assignment_logger=AssignmentLogger()
    )
    assert client.get_assignment("user-1", "experiment-key-1") is None


@pytest.mark.parametrize("test_case", test_data)
def test_assign_subject_in_sample(test_case):
    print("---- Test case for {} Experiment".format(test_case["experiment"]))
    assignments = get_assignments(test_case=test_case)
    assert assignments == test_case["expectedAssignments"]


def get_assignments(test_case):
    client = get_instance()
    get_typed_assignment = {
        "string": client.get_string_assignment,
        "numeric": client.get_numeric_assignment,
        "boolean": client.get_boolean_assignment,
        "json": client.get_json_string_assignment,
    }
    return [
        get_typed_assignment[test_case["valueType"]](
            subjectKey, test_case["experiment"]
        )
        for subjectKey in test_case.get("subjects", [])
    ] + [
        get_typed_assignment[test_case["valueType"]](
            subject_key=subject["subjectKey"],
            flag_key=test_case["experiment"],
            subject_attributes=subject["subjectAttributes"],
        )
        for subject in test_case.get("subjectsWithAttributes", [])
    ]
