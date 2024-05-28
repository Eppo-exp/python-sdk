import pytest

from eppo_client.sharders import MD5Sharder, DeterministicSharder

from eppo_client.bandit import (
    ActionContext,
    Attributes,
    score_numeric_attributes,
    score_categorical_attributes,
    BanditEvaluator,
)
from eppo_client.models import (
    BanditCoefficients,
    BanditModelData,
    BanditNumericAttributeCoefficient,
    BanditCategoricalAttributeCoefficient,
)

bandit_evaluator = BanditEvaluator(MD5Sharder(), 10_000)


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
    assert (
        bandit_evaluator.weight_actions(action_scores, gamma, probability_floor)
        == expected_weights
    )


def test_weight_actions_multiple_actions():
    action_scores = [("action1", 1.0), ("action2", 0.5)]
    gamma = 0.1
    probability_floor = 0.1
    weights = bandit_evaluator.weight_actions(action_scores, gamma, probability_floor)
    assert len(weights) == 2
    assert any(action == "action1" and weight > 0.5 for action, weight in weights)
    assert any(action == "action2" and weight <= 0.5 for action, weight in weights)


def test_weight_actions_probability_floor():
    action_scores = [("action1", 1.0), ("action2", 0.5), ("action3", 0.2)]
    gamma = 0.1
    probability_floor = 0.3
    weights = bandit_evaluator.weight_actions(action_scores, gamma, probability_floor)
    assert len(weights) == 3
    for action, weight in weights:
        assert weight >= 0.1


def test_weight_actions_gamma_effect():
    action_scores = [("action1", 1.0), ("action2", 0.5)]
    gamma = 1.0
    probability_floor = 0.1
    weights = bandit_evaluator.weight_actions(action_scores, gamma, probability_floor)
    assert len(weights) == 2
    assert any(action == "action1" and weight > 0.5 for action, weight in weights)
    assert any(action == "action2" and weight <= 0.5 for action, weight in weights)


def test_weight_actions_all_equal_scores():
    action_scores = [("action1", 1.0), ("action2", 1.0), ("action3", 1.0)]
    gamma = 0.1
    probability_floor = 0.1
    weights = bandit_evaluator.weight_actions(action_scores, gamma, probability_floor)
    assert len(weights) == 3
    for _, weight in weights:
        assert weight == pytest.approx(1.0 / 3, rel=1e-2)


def test_evaluate_bandit():
    # Mock data
    flag_key = "test_flag"
    subject_key = "test_subject"
    subject_attributes = Attributes(
        numeric_attributes={"age": 25.0}, categorical_attributes={"location": "US"}
    )
    action_contexts = [
        ActionContext(
            action_key="action1",
            attributes=Attributes(
                numeric_attributes={"price": 10.0},
                categorical_attributes={"category": "A"},
            ),
        ),
        ActionContext(
            action_key="action2",
            attributes=Attributes(
                numeric_attributes={"price": 20.0},
                categorical_attributes={"category": "B"},
            ),
        ),
    ]
    coefficients = {
        "action1": BanditCoefficients(
            action_key="action1",
            intercept=0.5,
            subject_numeric_coefficients=[
                BanditNumericAttributeCoefficient(
                    attribute_key="age", coefficient=0.1, missing_value_coefficient=0.0
                )
            ],
            subject_categorical_coefficients=[
                BanditCategoricalAttributeCoefficient(
                    attribute_key="location",
                    missing_value_coefficient=0.0,
                    value_coefficients={"US": 0.2},
                )
            ],
            action_numeric_coefficients=[
                BanditNumericAttributeCoefficient(
                    attribute_key="price",
                    coefficient=0.05,
                    missing_value_coefficient=0.0,
                )
            ],
            action_categorical_coefficients=[
                BanditCategoricalAttributeCoefficient(
                    attribute_key="category",
                    missing_value_coefficient=0.0,
                    value_coefficients={"A": 0.3},
                )
            ],
        ),
        "action2": BanditCoefficients(
            action_key="action2",
            intercept=0.3,
            subject_numeric_coefficients=[
                BanditNumericAttributeCoefficient(
                    attribute_key="age", coefficient=0.1, missing_value_coefficient=0.0
                )
            ],
            subject_categorical_coefficients=[
                BanditCategoricalAttributeCoefficient(
                    attribute_key="location",
                    missing_value_coefficient=0.0,
                    value_coefficients={"US": 0.2},
                )
            ],
            action_numeric_coefficients=[
                BanditNumericAttributeCoefficient(
                    attribute_key="price",
                    coefficient=0.05,
                    missing_value_coefficient=0.0,
                )
            ],
            action_categorical_coefficients=[
                BanditCategoricalAttributeCoefficient(
                    attribute_key="category",
                    missing_value_coefficient=0.0,
                    value_coefficients={"B": 0.3},
                )
            ],
        ),
    }
    bandit_model = BanditModelData(
        gamma=0.1,
        default_action_score=0.0,
        action_probability_floor=0.1,
        coefficients=coefficients,
    )

    evaluator = BanditEvaluator(sharder=DeterministicSharder({}))

    # Evaluate bandit
    evaluation = evaluator.evaluate_bandit(
        flag_key, subject_key, subject_attributes, action_contexts, bandit_model
    )

    # Assertions
    assert evaluation.flag_key == flag_key
    assert evaluation.subject_key == subject_key
    assert evaluation.subject_attributes == subject_attributes
    assert evaluation.action_key == "action1"
    assert evaluation.gamma == bandit_model.gamma
    assert evaluation.action_score == 4.0
    assert pytest.approx(evaluation.action_weight, rel=1e-2) == 0.4926
