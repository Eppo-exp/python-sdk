# Note: contains tests for client.py related to bandits to avoid
# making client_test.py too long.


import json
import os
from time import sleep
from typing import Dict, List
from unittest.mock import patch
from eppo_client.bandit import BanditEvaluator, BanditResult, ContextAttributes

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


MOCK_BASE_URL = "http://localhost:4001/api"

DEFAULT_SUBJECT_ATTRIBUTES = ContextAttributes(
    numeric_attributes={"age": 30}, categorical_attributes={"country": "UK"}
)


class MockAssignmentLogger(AssignmentLogger):
    assignment_events: List[Dict] = []
    bandit_events: List[Dict] = []

    def log_assignment(self, assignment_event: Dict):
        self.assignment_events.append(assignment_event)

    def log_bandit_action(self, bandit_event: Dict):
        self.bandit_events.append(bandit_event)


mock_assignment_logger = MockAssignmentLogger()


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
            assignment_logger=mock_assignment_logger,
            is_graceful_mode=False,
        )
    )
    sleep(0.1)  # wait for initialization
    yield
    client._shutdown()
    httpretty.disable()
    httpretty.reset()

@pytest.fixture(autouse=True)
def clear_event_arrays():
    # Reset graceful mode to off
    get_instance().set_is_graceful_mode(False)
    # Clear captured logger events 
    mock_assignment_logger.assignment_events.clear()
    mock_assignment_logger.bandit_events.clear()

def test_is_initialized():
    client = get_instance()
    assert client.is_initialized(), "Client should be initialized"


def test_get_bandit_action_flag_not_exist():
    client = get_instance()
    result = client.get_bandit_action(
        "nonexistent_flag",
        "subject_key",
        DEFAULT_SUBJECT_ATTRIBUTES,
        {},
        "default_variation",
    )
    assert result == BanditResult("default_variation", None)


def test_get_bandit_action_flag_has_no_bandit():
    client = get_instance()
    result = client.get_bandit_action(
        "non_bandit_flag", "subject_key", DEFAULT_SUBJECT_ATTRIBUTES, {}, "default_variation"
    )
    assert result == BanditResult("control", None)

@patch.object(BanditEvaluator, 'evaluate_bandit', side_effect=Exception("Mocked Exception"))
def test_get_bandit_action_bandit_error(mock_bandit_evaluator):
    client = get_instance()
    client.set_is_graceful_mode(True)
    actions = {
        "adidas": ContextAttributes(
            numeric_attributes={"discount": 0.1},
            categorical_attributes={"from": "germany"},
        ),
        "nike": ContextAttributes(
            numeric_attributes={"discount": 0.2}, categorical_attributes={"from": "usa"}
        ),
    }

    result = client.get_bandit_action(
        "banner_bandit_flag_uk_only",
        "alice",
        DEFAULT_SUBJECT_ATTRIBUTES,
        actions,
        "default_variation",
    )
    assert result.variation == "banner_bandit"
    assert result.action is None

    # testing assignment logger
    assignment_log_statement = mock_assignment_logger.assignment_events[-1]
    assert assignment_log_statement["featureFlag"] == "banner_bandit_flag_uk_only"
    assert assignment_log_statement["variation"] == "banner_bandit"
    assert assignment_log_statement["subject"] == "alice"

    # testing bandit logger
    assert len(mock_assignment_logger.bandit_events) == 0


def test_get_bandit_action_with_subject_attributes():
    # tests that allocation filtering based on subject attributes works correctly
    client = get_instance()
    actions = {
        "adidas": ContextAttributes(
            numeric_attributes={"discount": 0.1},
            categorical_attributes={"from": "germany"},
        ),
        "nike": ContextAttributes(
            numeric_attributes={"discount": 0.2}, categorical_attributes={"from": "usa"}
        ),
    }
    result = client.get_bandit_action(
        "banner_bandit_flag_uk_only",
        "alice",
        DEFAULT_SUBJECT_ATTRIBUTES,
        actions,
        "default_variation",
    )
    assert result.variation == "banner_bandit"
    assert result.action in ["adidas", "nike"]

    # testing assignment logger
    assignment_log_statement = mock_assignment_logger.assignment_events[-1]
    assert assignment_log_statement["featureFlag"] == "banner_bandit_flag_uk_only"
    assert assignment_log_statement["variation"] == "banner_bandit"
    assert assignment_log_statement["subject"] == "alice"

    # testing bandit logger
    bandit_log_statement = mock_assignment_logger.bandit_events[-1]
    assert bandit_log_statement["flagKey"] == "banner_bandit_flag_uk_only"
    assert bandit_log_statement["banditKey"] == "banner_bandit"
    assert bandit_log_statement["subject"] == "alice"
    assert (
        bandit_log_statement["subjectNumericAttributes"]
        == DEFAULT_SUBJECT_ATTRIBUTES.numeric_attributes
    )
    assert (
        bandit_log_statement["subjectCategoricalAttributes"]
        == DEFAULT_SUBJECT_ATTRIBUTES.categorical_attributes
    )
    assert bandit_log_statement["action"] == result.action
    assert bandit_log_statement["optimalityGap"] >= 0
    assert bandit_log_statement["actionProbability"] >= 0

    chosen_action = actions[result.action]

    assert (
        bandit_log_statement["actionNumericAttributes"]
        == chosen_action.numeric_attributes
    )
    assert (
        bandit_log_statement["actionCategoricalAttributes"]
        == chosen_action.categorical_attributes
    )

@patch.object(MockAssignmentLogger, 'log_bandit_action', side_effect=Exception("Mocked Exception"))
def test_get_bandit_action_bandit_logger_error(patched_mock_assignment_logger):
    client = get_instance()
    actions = {
        "adidas": ContextAttributes(
            numeric_attributes={"discount": 0.1},
            categorical_attributes={"from": "germany"},
        ),
        "nike": ContextAttributes(
            numeric_attributes={"discount": 0.2}, categorical_attributes={"from": "usa"}
        ),
    }
    result = client.get_bandit_action(
        "banner_bandit_flag_uk_only",
        "alice",
        DEFAULT_SUBJECT_ATTRIBUTES,
        actions,
        "default_variation",
    )
    assert result.variation == "banner_bandit"
    assert result.action in ["adidas", "nike"]

    # assignment should have still been logged
    assert len(mock_assignment_logger.assignment_events) == 1
    assert len(mock_assignment_logger.bandit_events) == 0
    

@pytest.mark.parametrize("test_case", test_data)
def test_bandit_generic_test_cases(test_case):
    client = get_instance()

    flag = test_case["flag"]
    default_value = test_case["defaultValue"]

    for subject in test_case["subjects"]:
        result = client.get_bandit_action(
            flag,
            subject["subjectKey"],
            ContextAttributes(
                numeric_attributes=subject["subjectAttributes"]["numericAttributes"],
                categorical_attributes=subject["subjectAttributes"][
                    "categoricalAttributes"
                ],
            ),
            {
                action["actionKey"]: ContextAttributes(
                    action["numericAttributes"], action["categoricalAttributes"]
                )
                for action in subject["actions"]
            },
            default_value,
        )

        expected_result = BanditResult(
            subject["assignment"]["variation"], subject["assignment"]["action"]
        )

        assert result.variation == expected_result.variation, (
            f"Flag {flag} failed for subject {subject['subjectKey']}:"
            f"expected assignment {expected_result.variation}, got {result.variation}"
        )
        assert result.action == expected_result.action, (
            f"Flag {flag} failed for subject {subject['subjectKey']}:"
            f"expected action {expected_result.action}, got {result.action}"
        )
