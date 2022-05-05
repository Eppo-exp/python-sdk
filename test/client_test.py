import json
import os
from time import sleep
from unittest.mock import patch
import httpretty  # type: ignore
import pytest
from eppo_client.client import EppoClient
from eppo_client.config import Config
from eppo_client.configuration_requestor import (
    ExperimentConfigurationDto,
    VariationDto,
)
from eppo_client.shard import ShardRange
from eppo_client import init, get_instance

test_data = []
for file_name in [file for file in os.listdir("test/test-data/assignment")]:
    with open("test/test-data/assignment/{}".format(file_name)) as test_case_json:
        test_case_dict = json.load(test_case_json)
        test_data.append(test_case_dict)

exp_configs = dict()
for experiment_test in test_data:
    experiment_name = experiment_test["experiment"]
    exp_configs[experiment_name] = {
        "subjectShards": 10000,
        "enabled": True,
        "variations": experiment_test["variations"],
        "name": experiment_name,
        "percentExposure": experiment_test["percentExposure"],
    }

MOCK_BASE_URL = "http://localhost:4000/api"


@pytest.fixture(scope="session", autouse=True)
def init_fixture():
    httpretty.enable()
    config_response_json = json.dumps({"experiments": exp_configs})
    httpretty.register_uri(
        httpretty.GET,
        MOCK_BASE_URL + "/randomized_assignment/config",
        body=config_response_json,
    )
    client = init(Config(base_url=MOCK_BASE_URL, api_key="dummy"))
    sleep(0.1)  # wait for initialization
    yield
    client._shutdown()
    httpretty.disable()


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_assign_blank_experiment(mock_config_requestor):
    client = EppoClient(config_requestor=mock_config_requestor)
    with pytest.raises(Exception) as exc_info:
        client.assign("subject-1", "")
    assert exc_info.value.args[0] == "Invalid value for experiment_key: cannot be blank"


@patch("eppo_client.configuration_requestor.ExperimentConfigurationRequestor")
def test_assign_blank_subject(mock_config_requestor):
    client = EppoClient(config_requestor=mock_config_requestor)
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
    assert client.assign("user-1", "experiment-key-1") is None


@pytest.mark.parametrize("test_case", test_data)
def test_assign_subject_in_sample(test_case):
    print("---- Test case for {} Experiment".format(test_case["experiment"]))
    client = get_instance()
    assignments = [
        client.assign(subject, test_case["experiment"])
        for subject in test_case["subjects"]
    ]
    assert assignments == test_case["expectedAssignments"]
