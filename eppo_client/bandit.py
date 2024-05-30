from dataclasses import dataclass
import logging
from typing import Dict, List, Optional, Tuple

from eppo_client.models import (
    BanditCategoricalAttributeCoefficient,
    BanditCoefficients,
    BanditModelData,
    BanditNumericAttributeCoefficient,
)
from eppo_client.sharders import Sharder


logger = logging.getLogger(__name__)


class BanditEvaluationError(Exception):
    pass


@dataclass
class Attributes:
    numeric_attributes: Dict[str, float]
    categorical_attributes: Dict[str, str]


@dataclass
class ActionContext:
    action_key: str
    attributes: Attributes

    @classmethod
    def create(
        cls,
        action_key: str,
        numeric_attributes: Dict[str, float],
        categorical_attributes: Dict[str, str],
    ):
        """
        Create an instance of ActionContext.

        Args:
            action_key (str): The key representing the action.
            numeric_attributes (Dict[str, float]): A dictionary of numeric attributes.
            categorical_attributes (Dict[str, str]): A dictionary of categorical attributes.

        Returns:
            ActionContext: An instance of ActionContext with the provided action key and attributes.
        """
        return cls(
            action_key,
            Attributes(
                numeric_attributes=numeric_attributes,
                categorical_attributes=categorical_attributes,
            ),
        )

    @property
    def numeric_attributes(self):
        return self.attributes.numeric_attributes

    @property
    def categorical_attributes(self):
        return self.attributes.categorical_attributes


@dataclass
class BanditEvaluation:
    flag_key: str
    subject_key: str
    subject_attributes: Attributes
    action_key: Optional[str]
    action_attributes: Optional[Attributes]
    action_score: float
    action_weight: float
    gamma: float


@dataclass
class BanditResult:
    variation: str
    action: Optional[str]

    def to_string(self) -> str:
        return coalesce(self.action, self.variation)


def null_evaluation(
    flag_key: str, subject_key: str, subject_attributes: Attributes, gamma: float
):
    return BanditEvaluation(
        flag_key,
        subject_key,
        subject_attributes,
        None,
        None,
        0.0,
        0.0,
        gamma,
    )


@dataclass
class BanditEvaluator:
    sharder: Sharder
    total_shards: int = 10_000

    def evaluate_bandit(
        self,
        flag_key: str,
        subject_key: str,
        subject_attributes: Attributes,
        actions_with_contexts: List[ActionContext],
        bandit_model: BanditModelData,
    ) -> BanditEvaluation:
        # handle the edge case that there are no actions
        if not actions_with_contexts:
            return null_evaluation(
                flag_key, subject_key, subject_attributes, bandit_model.gamma
            )

        action_scores = self.score_actions(
            subject_attributes, actions_with_contexts, bandit_model
        )

        action_weights = self.weigh_actions(
            action_scores,
            bandit_model.gamma,
            bandit_model.action_probability_floor,
        )

        selected_idx, selected_action = self.select_action(
            flag_key, subject_key, action_weights
        )
        return BanditEvaluation(
            flag_key,
            subject_key,
            subject_attributes,
            selected_action,
            actions_with_contexts[selected_idx].attributes,
            action_scores[selected_idx][1],
            action_weights[selected_idx][1],
            bandit_model.gamma,
        )

    def score_actions(
        self,
        subject_attributes: Attributes,
        actions_with_contexts: List[ActionContext],
        bandit_model: BanditModelData,
    ) -> List[Tuple[str, float]]:
        return [
            (
                action_context.action_key,
                (
                    score_action(
                        subject_attributes,
                        action_context.attributes,
                        bandit_model.coefficients[action_context.action_key],
                    )
                    if action_context.action_key in bandit_model.coefficients
                    else bandit_model.default_action_score
                ),
            )
            for action_context in actions_with_contexts
        ]

    def weigh_actions(
        self, action_scores, gamma, probability_floor
    ) -> List[Tuple[str, float]]:
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
        remaining_weight = max(0.0, 1.0 - sum(weight for _, weight in weights))
        weights.append((best_action, remaining_weight))
        return weights

    def select_action(self, flag_key, subject_key, action_weights) -> Tuple[int, str]:
        # deterministic ordering
        sorted_action_weights = sorted(
            action_weights,
            key=lambda t: (
                self.sharder.get_shard(
                    f"{flag_key}-{subject_key}-{t[0]}", self.total_shards
                ),
                t[0],  # tie-break using action name
            ),
        )

        # select action based on weights
        shard = self.sharder.get_shard(f"{flag_key}-{subject_key}", self.total_shards)
        cumulative_weight = 0.0
        shard_value = shard / self.total_shards

        for idx, (action_key, weight) in enumerate(sorted_action_weights):
            cumulative_weight += weight
            if cumulative_weight > shard_value:
                return idx, action_key

        # If no action is selected, return the last action (fallback)
        raise BanditEvaluationError(
            f"[Eppo SDK] No action selected for {flag_key} {subject_key}"
        )


def score_action(
    subject_attributes: Attributes,
    action_attributes: Attributes,
    coefficients: BanditCoefficients,
) -> float:
    score = coefficients.intercept
    score += score_numeric_attributes(
        coefficients.subject_numeric_coefficients,
        subject_attributes.numeric_attributes,
    )
    score += score_categorical_attributes(
        coefficients.subject_categorical_coefficients,
        subject_attributes.categorical_attributes,
    )
    score += score_numeric_attributes(
        coefficients.action_numeric_coefficients,
        action_attributes.numeric_attributes,
    )
    score += score_categorical_attributes(
        coefficients.action_categorical_coefficients,
        action_attributes.categorical_attributes,
    )
    return score


def coalesce(value, default=0):
    return value if value is not None else default


def score_numeric_attributes(
    coefficients: List[BanditNumericAttributeCoefficient],
    attributes: Dict[str, float],
) -> float:
    score = 0.0
    for coefficient in coefficients:
        if (
            coefficient.attribute_key in attributes
            and attributes[coefficient.attribute_key] is not None
        ):
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
