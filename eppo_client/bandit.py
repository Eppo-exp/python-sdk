from dataclasses import dataclass
from typing import Dict, List, Tuple
from eppo_client.models import (
    ActionContext,
    Attributes,
    BanditCategoricalAttributeCoefficient,
    BanditCoefficients,
    BanditModelData,
    BanditNumericAttributeCoefficient,
)
from eppo_client.sharders import Sharder


@dataclass
class BanditEvaluator:
    sharder: Sharder
    total_shards: int = 10_000

    def evaluate_bandit(
        self,
        flag_key: str,
        subject_key: str,
        subject_attributes: Attributes,
        action_attributes: Attributes,
        actions_with_contexts: List[ActionContext],
        bandit_model: BanditModelData,
    ):
        action_scores = self.score_actions(
            subject_attributes, action_attributes, actions_with_contexts, bandit_model
        )

        action_weights = self.weight_actions(
            action_scores,
            bandit_model.gamma,
            bandit_model.action_probability_floor,
        )

        selected_action = self.select_action(flag_key, subject_key, action_weights)
        return selected_action

    def score_actions(
        self,
        subject_attributes: Attributes,
        action_attributes: Attributes,
        actions_with_contexts: List[ActionContext],
        bandit_model: BanditModelData,
    ):
        return [
            (
                action_context.action_key,
                (
                    score_action(
                        subject_attributes,
                        action_attributes,
                        bandit_model.coefficients[action_context.action_key],
                    )
                    if action_context.action_key in bandit_model.coefficients
                    else bandit_model.default_action_score
                ),
            )
            for action_context in actions_with_contexts
        ]

    def weight_actions(self, action_scores, gamma, probability_floor):
        number_of_actions = len(action_scores)
        best_action, best_score = max(action_scores, key=lambda t: t[1])

        # adjust probability floor for number of actions to control the sum
        min_probability = probability_floor / number_of_actions

        # weight all but the best action
        weights = [
            (
                action_key,
                max(
                    min_probability,
                    1.0 / (number_of_actions + gamma * (best_score - score)),
                ),
            )
            for action_key, score in action_scores
            if action_key != best_action
        ]

        # remaining weight goes to best action
        remaining_weight = 1.0 - sum(weight for _, weight in weights)
        weights.append((best_action, remaining_weight))
        return weights

    def select_action(self, flag_key, subject_key, action_weights) -> Tuple[str, float]:
        # deterministic ordering
        sorted_action_weights = sorted(
            action_weights,
            key=lambda t: self.sharder.get_shard(
                f"{flag_key}-{subject_key}-{t[0]}", self.total_shards
            ),
        )

        # select action based on weights
        shard = self.sharder.get_shard(f"{flag_key}-{subject_key}", self.total_shards)
        cumulative_weight = 0.0
        shard_value = shard / self.total_shards

        for action_key, weight in sorted_action_weights:
            cumulative_weight += weight
            if cumulative_weight > shard_value:
                return action_key, weight

        # If no action is selected, return the last action (fallback)
        return sorted_action_weights[-1]


def score_action(
    subject_attributes: Attributes,
    action_attributes: Attributes,
    coefficients: BanditCoefficients,
):
    score = coefficients.intercept
    score += score_numeric_attributes(
        subject_attributes.numeric_attributes, coefficients.subject_numeric_coefficients
    )
    score += score_categorical_attributes(
        subject_attributes.categorical_attributes,
        coefficients.subject_categorical_coefficients,
    )
    score += score_numeric_attributes(
        action_attributes.numeric_attributes, coefficients.action_numeric_coefficients
    )
    score += score_numeric_attributes(
        action_attributes.numeric_attributes, coefficients.action_numeric_coefficients
    )
    return score


def score_numeric_attributes(
    coefficients: List[BanditNumericAttributeCoefficient],
    attributes: Dict[str, float],
) -> float:
    score = 0.0
    for coefficient in coefficients:
        if coefficient.attribute_key in attributes:
            score += coefficient.coefficient * attributes[coefficient.attribute_key]
        else:
            score += coefficient.missing_value_coefficient

    return score


def score_categorical_attributes(
    coefficients: List[BanditCategoricalAttributeCoefficient],
    attributes: Dict[str, str],
) -> float:
    score = 0.0
    for coefficient in coefficients:
        if coefficient.attribute_key in attributes:
            score += coefficient.value_coefficients.get(
                attributes[coefficient.attribute_key],
                coefficient.missing_value_coefficient,
            )
        else:
            score += coefficient.missing_value_coefficient
    return score
