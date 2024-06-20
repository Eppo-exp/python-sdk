import json
import os
from time import sleep
from unittest.mock import patch
import httpretty  # type: ignore
import pytest
from eppo_client.assignment_logger import AssignmentLogger
from eppo_client.client import EppoClient, check_type_match, check_value_type_match
from eppo_client.config import Config
from eppo_client.models import (
    Allocation,
    Flag,
    Range,
    Shard,
    Split,
    VariationType,
    Variation,
)
from eppo_client import init, get_instance

import logging

logger = logging.getLogger(__name__)

TEST_DIR = "test/test-data/ufc/tests"
CONFIG_FILE = "test/test-data/ufc/flags-v1.json"
test_data = []
for file_name in [file for file in os.listdir(TEST_DIR)]:
    with open("{}/{}".format(TEST_DIR, file_name)) as test_case_json:
        test_case_dict = json.load(test_case_json)
        test_data.append(test_case_dict)

MOCK_BASE_URL = "http://localhost:4001/api"


@pytest.fixture(scope="session", autouse=True)
def init_fixture():
    httpretty.enable()
    with open(CONFIG_FILE) as mock_ufc_response:
        httpretty.register_uri(
            httpretty.GET,
            MOCK_BASE_URL + "/flag-config/v1/config",
            body=json.dumps(json.load(mock_ufc_response)),
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


def test_is_initialized():
    client = get_instance()
    assert client.is_initialized()


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_assign_blank_flag_key(mock_config_requestor):
    client = EppoClient(
        config_requestor=mock_config_requestor, assignment_logger=AssignmentLogger()
    )
    with pytest.raises(Exception) as exc_info:
        client.get_string_assignment("", "subject-1", {}, "default value")
    assert exc_info.value.args[0] == "Invalid value for flag_key: cannot be blank"


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_assign_blank_subject(mock_config_requestor):
    client = EppoClient(
        config_requestor=mock_config_requestor, assignment_logger=AssignmentLogger()
    )
    with pytest.raises(Exception) as exc_info:
        client.get_string_assignment("experiment-1", "", {}, "default value")
    assert exc_info.value.args[0] == "Invalid value for subject_key: cannot be blank"


@patch("eppo_client.assignment_logger.AssignmentLogger")
@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_log_assignment(mock_config_requestor, mock_logger):
    flag = Flag(
        key="flag-key",
        enabled=True,
        variation_type=VariationType.STRING,
        variations={"control": Variation(key="control", value="control")},
        allocations=[
            Allocation(
                key="allocation",
                splits=[
                    Split(
                        variation_key="control",
                        shards=[Shard(salt="salt", ranges=[Range(start=0, end=10000)])],
                    )
                ],
            )
        ],
        total_shards=10_000,
    )

    mock_config_requestor.get_configuration.return_value = flag
    client = EppoClient(
        config_requestor=mock_config_requestor, assignment_logger=mock_logger
    )
    assert (
        client.get_string_assignment("falg-key", "user-1", {}, "default value")
        == "control"
    )
    assert mock_logger.log_assignment.call_count == 1


@patch("eppo_client.assignment_logger.AssignmentLogger")
@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_get_assignment_handles_logging_exception(mock_config_requestor, mock_logger):
    flag = Flag(
        key="flag-key",
        enabled=True,
        variation_type=VariationType.STRING,
        variations={"control": Variation(key="control", value="control")},
        allocations=[
            Allocation(
                key="allocation",
                rules=[],
                splits=[
                    Split(
                        variation_key="control",
                        shards=[Shard(salt="salt", ranges=[Range(start=0, end=10000)])],
                    )
                ],
            )
        ],
        total_shards=10_000,
    )

    mock_config_requestor.get_configuration.return_value = flag
    mock_logger.log_assignment.side_effect = ValueError("logging error")

    client = EppoClient(
        config_requestor=mock_config_requestor, assignment_logger=mock_logger
    )
    assert (
        client.get_string_assignment("flag-key", "user-1", {}, "default value")
        == "control"
    )


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_with_null_experiment_config(mock_config_requestor):
    mock_config_requestor.get_configuration.return_value = None
    client = EppoClient(
        config_requestor=mock_config_requestor, assignment_logger=AssignmentLogger()
    )
    assert (
        client.get_string_assignment("flag-key-1", "user-1", {}, "default value")
        == "default value"
    )
    assert (
        client.get_string_assignment("flag-key-1", "user-1", {}, "hello world")
        == "hello world"
    )


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
@patch.object(EppoClient, "get_assignment_detail")
def test_graceful_mode_on(get_assignment_detail, mock_config_requestor):
    get_assignment_detail.side_effect = Exception("This is a mock exception!")

    client = EppoClient(
        config_requestor=mock_config_requestor,
        assignment_logger=AssignmentLogger(),
        is_graceful_mode=True,
    )

    assert (
        client.get_assignment_variation(
            "experiment-key-1", "user-1", {}, "default", VariationType.STRING
        )
        == "default"
    )
    assert client.get_boolean_assignment("experiment-key-1", "user-1", {}, default=True)
    assert client.get_numeric_assignment("experiment-key-1", "user-1", {}, 1.0) == 1.0
    assert (
        client.get_string_assignment(
            "experiment-key-1", "user-1", {}, default="control"
        )
        == "control"
    )
    assert client.get_json_assignment(
        "experiment-key-1", "user-1", {}, {"hello": "world"}
    ) == {"hello": "world"}


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
@patch.object(EppoClient, "get_assignment_detail")
def test_graceful_mode_off(mock_get_assignment_detail, mock_config_requestor):
    mock_get_assignment_detail.side_effect = Exception("This is a mock exception!")

    client = EppoClient(
        config_requestor=mock_config_requestor,
        assignment_logger=AssignmentLogger(),
        is_graceful_mode=False,
    )

    with pytest.raises(Exception):
        client.get_boolean_assignment("experiment-key-1", "user-1", {}, True)
        client.get_numeric_assignment("experiment-key-1", "user-1", {}, 0.0)
        client.get_integer_assignment("experiment-key-1", "user-1", {}, 1)
        client.get_string_assignment("experiment-key-1", "user-1", {}, "default value")
        client.get_json_assignment("experiment-key-1", "user-1", {}, {"hello": "world"})


def test_client_has_flags():
    client = get_instance()
    assert len(client.get_flag_keys()) > 0, "No flags have been loaded by the client"


def test_client_flag_configurations():
    client = get_instance()
    assert len(
        client.get_flag_configurations()
    ) > 0, "No flags have been loaded by the client"


@pytest.mark.parametrize("test_case", test_data)
def test_assign_subject_in_sample(test_case):
    client = get_instance()
    print("---- Test case for {} Experiment".format(test_case["flag"]))

    get_typed_assignment = {
        "STRING": client.get_string_assignment,
        "INTEGER": client.get_integer_assignment,
        "NUMERIC": client.get_numeric_assignment,
        "BOOLEAN": client.get_boolean_assignment,
        "JSON": client.get_json_assignment,
    }[test_case["variationType"]]

    assignments = get_assignments(test_case, get_typed_assignment)
    for subject, assigned_variation in assignments:
        assert (
            assigned_variation == subject["assignment"]
        ), f"expected <{subject['assignment']}> for subject {subject['subjectKey']}, found <{assigned_variation}>"


def get_assignments(test_case, get_assignment_fn):
    client = get_instance()
    client.__is_graceful_mode = False

    print(test_case["flag"])
    assignments = []
    for subject in test_case.get("subjects", []):
        variation = get_assignment_fn(
            test_case["flag"],
            subject["subjectKey"],
            subject["subjectAttributes"],
            test_case["defaultValue"],
        )
        assignments.append((subject, variation))
    return assignments


@pytest.mark.parametrize("test_case", test_data)
def test_get_numeric_assignment_on_bool_feature_flag_should_return_none(test_case):
    client = get_instance()
    if test_case["variationType"] == "boolean":
        assignments = get_assignments(
            test_case=test_case, get_assignment_fn=client.get_numeric_assignment
        )
        for _, assigned_variation in assignments:
            assert assigned_variation is None

        assignments = get_assignments(
            test_case=test_case, get_assignment_fn=client.get_integer_assignment
        )
        for _, assigned_variation in assignments:
            assert assigned_variation is None


def test_check_type_match():
    assert check_type_match(VariationType.STRING, VariationType.STRING)
    assert check_type_match(None, VariationType.STRING)


def test_check_value_type_match():
    assert check_value_type_match(VariationType.STRING, "hello")
    assert check_value_type_match(VariationType.INTEGER, 1)
    assert check_value_type_match(VariationType.NUMERIC, 1.0)
    assert check_value_type_match(VariationType.NUMERIC, 1)
    assert check_value_type_match(VariationType.BOOLEAN, True)
    assert check_value_type_match(VariationType.JSON, '{"hello": "world"}')

    assert not check_type_match(VariationType.STRING, 1)
    assert not check_type_match(VariationType.INTEGER, 1.0)
    assert not check_type_match(VariationType.BOOLEAN, "true")
