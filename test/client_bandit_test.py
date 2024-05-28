# Note: contains tests for client.py related to bandits to avoid
# making client_test.py too long.


import json
import os
from time import sleep
from typing import Dict
from eppo_client.bandit import BanditResult, ActionContext, Attributes

import httpretty  # type: ignore
import pytest

from eppo_client.assignment_logger import AssignmentLogger
from eppo_client.configuration_requestor import BANDIT_ENDPOINT, UFC_ENDPOINT
from eppo_client import init, get_instance
from eppo_client.config import Config

TEST_DIR = "test/test-data/ufc/bandit-tests"
FLAG_CONFIG_FILE = "test/test-data/ufc/bandit-flags-v1.json"
BANDIT_CONFIG_FILE = "test/test-data/ufc/bandit-models-v1.json"
test_data = []
for file_name in [file for file in os.listdir(TEST_DIR)]:
    with open("{}/{}".format(TEST_DIR, file_name)) as test_case_json:
        test_case_dict = json.load(test_case_json)
        test_data.append(test_case_dict)

print(test_data)

MOCK_BASE_URL = "http://localhost:4001/api"

DEFAULT_SUBJECT_ATTRIBUTES = Attributes(
    numeric_attributes={"age": 30}, categorical_attributes={"country": "UK"}
)


class MockAssignmentLogger(AssignmentLogger):
    def log_assignment(self, assignment_event: Dict):
        print(f"Assignment Event: {assignment_event}")

    def log_bandit_action(self, bandit_event: Dict):
        print(f"Bandit Event: {bandit_event}")


@pytest.fixture(scope="session", autouse=True)
def init_fixture():
    httpretty.enable()
    with open(FLAG_CONFIG_FILE) as mock_ufc_response:
        ufc_json = json.load(mock_ufc_response)

    with open(BANDIT_CONFIG_FILE) as mock_bandit_response:
        bandit_json = json.load(mock_bandit_response)

    httpretty.register_uri(
        httpretty.GET,
        MOCK_BASE_URL + UFC_ENDPOINT,
        body=json.dumps(ufc_json),
    )
    httpretty.register_uri(
        httpretty.GET,
        MOCK_BASE_URL + BANDIT_ENDPOINT,
        body=json.dumps(bandit_json),
    )
    client = init(
        Config(
            base_url=MOCK_BASE_URL,
            api_key="dummy",
            assignment_logger=AssignmentLogger(),
        )
    )
    sleep(0.1)  # wait for initialization
    print(client.get_flag_keys())
    print(client.get_bandit_keys())
    yield
    client._shutdown()
    httpretty.disable()
    httpretty.reset()


def test_is_initialized():
    client = get_instance()
    assert client.is_initialized(), "Client should be initialized"


def test_get_bandit_action_bandit_does_not_exist():
    client = get_instance()
    result = client.get_bandit_action(
        "nonexistent_bandit",
        "subject_key",
        DEFAULT_SUBJECT_ATTRIBUTES,
        [],
        "default_variation",
    )
    print(result)
    assert result == BanditResult("default_variation", None)


def test_get_bandit_action_flag_without_bandit():
    client = get_instance()
    result = client.get_bandit_action(
        "a_flag", "subject_key", DEFAULT_SUBJECT_ATTRIBUTES, [], "default_variation"
    )
    assert result == BanditResult("default_variation", None)


def test_get_bandit_action_with_subject_attributes():
    # tests that allocation filtering based on subject attributes works correctly
    client = get_instance()
    result = client.get_bandit_action(
        "banner_bandit_flag_uk_only",
        "subject_key",
        DEFAULT_SUBJECT_ATTRIBUTES,
        [ActionContext.create("adidas", {}, {}), ActionContext.create("nike", {}, {})],
        "default_variation",
    )
    assert result.variation == "banner_bandit"
    assert result.action in ["adidas", "nike"]


@pytest.mark.parametrize("test_case", test_data)
def test_bandit_generic_test_cases(test_case):
    client = get_instance()

    flag = test_case["flag"]
    default_value = test_case["defaultValue"]

    for subject in test_case["subjects"]:
        result = client.get_bandit_action(
            flag,
            subject["subjectKey"],
            Attributes(
                numeric_attributes=subject["subjectAttributes"]["numeric_attributes"],
                categorical_attributes=subject["subjectAttributes"][
                    "categorical_attributes"
                ],
            ),
            [
                ActionContext.create(
                    action["actionKey"],
                    action["numericAttributes"],
                    action["categoricalAttributes"],
                )
                for action in subject["actions"]
            ],
            default_value,
        )

        expected_result = BanditResult(
            subject["assignment"]["variation"], subject["assignment"]["action"]
        )

        assert (
            result.variation == expected_result.variation
        ), f"Flag {flag} failed for subject {subject['subjectKey']}: expected assignment {expected_result.variation}, got {result.variation}"
        assert (
            result.action == expected_result.action
        ), f"Flag {flag} failed for subject {subject['subjectKey']}: expected action {expected_result.action}, got {result.action}"
