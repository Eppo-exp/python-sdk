import pytest

from eppo_client.bandit import (
    score_numeric_attributes,
    score_categorical_attributes,
    weight_actions,
)
from eppo_client.models import (
    BanditNumericAttributeCoefficient,
    BanditCategoricalAttributeCoefficient,
)


def test_score_numeric_attributes_all_present():
    coefficients = [
        BanditNumericAttributeCoefficient(
            attribute_key="age", coefficient=2.0, missing_value_coefficient=0.5
        ),
        BanditNumericAttributeCoefficient(
            attribute_key="height", coefficient=1.5, missing_value_coefficient=0.3
        ),
    ]
    attributes = {"age": 30, "height": 170}
    expected_score = 30 * 2.0 + 170 * 1.5
    assert score_numeric_attributes(coefficients, attributes) == expected_score


def test_score_numeric_attributes_some_missing():
    coefficients = [
        BanditNumericAttributeCoefficient(
            attribute_key="age", coefficient=2.0, missing_value_coefficient=0.5
        ),
        BanditNumericAttributeCoefficient(
            attribute_key="height", coefficient=1.5, missing_value_coefficient=0.3
        ),
    ]
    attributes = {"age": 30}
    expected_score = 30 * 2.0 + 0.3  # height is missing, use missing_value_coefficient
    assert score_numeric_attributes(coefficients, attributes) == expected_score


def test_score_numeric_attributes_all_missing():
    coefficients = [
        BanditNumericAttributeCoefficient(
            attribute_key="age", coefficient=2.0, missing_value_coefficient=0.5
        ),
        BanditNumericAttributeCoefficient(
            attribute_key="height", coefficient=1.5, missing_value_coefficient=0.3
        ),
    ]
    attributes = {}
    expected_score = 0.5 + 0.3  # both are missing, use missing_value_coefficients
    assert score_numeric_attributes(coefficients, attributes) == expected_score


def test_score_numeric_attributes_empty_coefficients():
    coefficients = []
    attributes = {"age": 30, "height": 170}
    expected_score = 0.0  # no coefficients to apply
    assert score_numeric_attributes(coefficients, attributes) == expected_score


def test_score_numeric_attributes_negative_coefficients():
    coefficients = [
        BanditNumericAttributeCoefficient(
            attribute_key="age", coefficient=-2.0, missing_value_coefficient=0.5
        ),
        BanditNumericAttributeCoefficient(
            attribute_key="height", coefficient=-1.5, missing_value_coefficient=0.3
        ),
    ]
    attributes = {"age": 30, "height": 170}
    expected_score = 30 * -2.0 + 170 * -1.5
    assert score_numeric_attributes(coefficients, attributes) == expected_score


def test_score_categorical_attributes_some_missing():
    coefficients = [
        BanditCategoricalAttributeCoefficient(
            attribute_key="color",
            missing_value_coefficient=0.2,
            value_coefficients={"red": 1.0, "blue": 0.5},
        ),
        BanditCategoricalAttributeCoefficient(
            attribute_key="size",
            missing_value_coefficient=0.3,
            value_coefficients={"large": 2.0, "small": 1.0},
        ),
    ]
    attributes = {"color": "red"}
    expected_score = 1.0 + 0.3  # size is missing, use missing_value_coefficient
    assert score_categorical_attributes(coefficients, attributes) == expected_score


def test_score_categorical_attributes_all_missing():
    coefficients = [
        BanditCategoricalAttributeCoefficient(
            attribute_key="color",
            missing_value_coefficient=0.2,
            value_coefficients={"red": 1.0, "blue": 0.5},
        ),
        BanditCategoricalAttributeCoefficient(
            attribute_key="size",
            missing_value_coefficient=0.3,
            value_coefficients={"large": 2.0, "small": 1.0},
        ),
    ]
    attributes = {}
    expected_score = 0.2 + 0.3  # both are missing, use missing_value_coefficients
    assert score_categorical_attributes(coefficients, attributes) == expected_score


def test_score_categorical_attributes_empty_coefficients():
    coefficients = []
    attributes = {"color": "red", "size": "large"}
    expected_score = 0.0  # no coefficients to apply
    assert score_categorical_attributes(coefficients, attributes) == expected_score


def test_score_categorical_attributes_negative_coefficients():
    coefficients = [
        BanditCategoricalAttributeCoefficient(
            attribute_key="color",
            missing_value_coefficient=0.2,
            value_coefficients={"red": -1.0, "blue": -0.5},
        ),
        BanditCategoricalAttributeCoefficient(
            attribute_key="size",
            missing_value_coefficient=0.3,
            value_coefficients={"large": -2.0, "small": -1.0},
        ),
    ]
    attributes = {"color": "red", "size": "large"}
    expected_score = -1.0 + -2.0
    assert score_categorical_attributes(coefficients, attributes) == expected_score


def test_score_categorical_attributes_mixed_coefficients():
    coefficients = [
        BanditCategoricalAttributeCoefficient(
            attribute_key="color",
            missing_value_coefficient=0.2,
            value_coefficients={"red": 1.0, "blue": -0.5},
        ),
        BanditCategoricalAttributeCoefficient(
            attribute_key="size",
            missing_value_coefficient=0.3,
            value_coefficients={"large": -2.0, "small": 1.0},
        ),
    ]
    attributes = {"color": "blue", "size": "small"}
    expected_score = -0.5 + 1.0
    assert score_categorical_attributes(coefficients, attributes) == expected_score


def test_weight_actions_single_action():
    action_scores = [("action1", 1.0)]
    gamma = 0.1
    probability_floor = 0.1
    expected_weights = [("action1", 1.0)]
    assert weight_actions(action_scores, gamma, probability_floor) == expected_weights


def test_weight_actions_multiple_actions():
    action_scores = [("action1", 1.0), ("action2", 0.5)]
    gamma = 0.1
    probability_floor = 0.1
    weights = weight_actions(action_scores, gamma, probability_floor)
    assert len(weights) == 2
    assert any(action == "action1" and weight > 0.5 for action, weight in weights)
    assert any(action == "action2" and weight <= 0.5 for action, weight in weights)


def test_weight_actions_probability_floor():
    action_scores = [("action1", 1.0), ("action2", 0.5), ("action3", 0.2)]
    gamma = 0.1
    probability_floor = 0.3
    weights = weight_actions(action_scores, gamma, probability_floor)
    assert len(weights) == 3
    for action, weight in weights:
        assert weight >= 0.1


def test_weight_actions_gamma_effect():
    action_scores = [("action1", 1.0), ("action2", 0.5)]
    gamma = 1.0
    probability_floor = 0.1
    weights = weight_actions(action_scores, gamma, probability_floor)
    assert len(weights) == 2
    assert any(action == "action1" and weight > 0.5 for action, weight in weights)
    assert any(action == "action2" and weight <= 0.5 for action, weight in weights)


def test_weight_actions_all_equal_scores():
    action_scores = [("action1", 1.0), ("action2", 1.0), ("action3", 1.0)]
    gamma = 0.1
    probability_floor = 0.1
    weights = weight_actions(action_scores, gamma, probability_floor)
    assert len(weights) == 3
    for _, weight in weights:
        assert weight == pytest.approx(1.0 / 3, rel=1e-2)
