from dataclasses import dataclass
import logging
from typing import Dict, List, Optional

from eppo_client.models import (
    BanditCategoricalAttributeCoefficient,
    BanditCoefficients,
    BanditModelData,
    BanditNumericAttributeCoefficient,
)
from eppo_client.rules import to_string
from eppo_client.sharders import Sharder
from eppo_client.types import Attributes


logger = logging.getLogger(__name__)


class BanditEvaluationError(Exception):
    pass


@dataclass
class ContextAttributes:
    numeric_attributes: Dict[str, float]
    categorical_attributes: Dict[str, str]

    @classmethod
    def empty(cls):
        """
        Create an empty Attributes instance with no numeric or categorical attributes.

        Returns:
            ContextAttributes: An instance of the ContextAttributes class with empty dictionaries
                for numeric and categorical attributes.
        """
        return cls({}, {})

    @classmethod
    def from_dict(cls, attributes: Attributes):
        """
        Create an ContextAttributes instance from a dictionary of attributes.

        Args:
            attributes (Dict[str, Union[float, int, bool, str]]): A dictionary where keys are attribute names
                and values are attribute values which can be of type float, int, bool, or str.

        Returns:
            ContextAttributes: An instance of the ContextAttributes class
                with numeric and categorical attributes separated.
        """
        numeric_attributes = {
            key: float(value)
            for key, value in attributes.items()
            if isinstance(value, (int, float))
        }
        categorical_attributes = {
            key: to_string(value)
            for key, value in attributes.items()
            if isinstance(value, (str, bool))
        }
        return cls(numeric_attributes, categorical_attributes)


ActionContexts = Dict[str, ContextAttributes]
ActionAttributes = Dict[str, Attributes]


@dataclass
class BanditEvaluation:
    flag_key: str
    subject_key: str
    subject_attributes: ContextAttributes
    action_key: Optional[str]
    action_attributes: Optional[ContextAttributes]
    action_score: float
    action_weight: float
    gamma: float
    optimality_gap: float


@dataclass
class BanditResult:
    variation: str
    action: Optional[str]

    def to_string(self) -> str:
        return coalesce(self.action, self.variation)


def null_evaluation(
    flag_key: str, subject_key: str, subject_attributes: ContextAttributes, gamma: float
):
    return BanditEvaluation(
        flag_key, subject_key, subject_attributes, None, None, 0.0, 0.0, gamma, 0.0
    )


@dataclass
class BanditEvaluator:
    sharder: Sharder
    total_shards: int = 10_000

    def evaluate_bandit(
        self,
        flag_key: str,
        subject_key: str,
        subject_attributes: ContextAttributes,
        actions: ActionContexts,
        bandit_model: BanditModelData,
    ) -> BanditEvaluation:
        # handle the edge case that there are no actions
        if not actions:
            return null_evaluation(
                flag_key, subject_key, subject_attributes, bandit_model.gamma
            )

        action_scores = self.score_actions(subject_attributes, actions, bandit_model)
        action_weights = self.weigh_actions(
            action_scores,
            bandit_model.gamma,
            bandit_model.action_probability_floor,
        )

        selected_action = self.select_action(flag_key, subject_key, action_weights)
        optimality_gap = max(action_scores.values()) - action_scores[selected_action]

        return BanditEvaluation(
            flag_key,
            subject_key,
            subject_attributes,
            selected_action,
            actions[selected_action],
            action_scores[selected_action],
            action_weights[selected_action],
            bandit_model.gamma,
            optimality_gap,
        )

    def score_actions(
        self,
        subject_attributes: ContextAttributes,
        actions: ActionContexts,
        bandit_model: BanditModelData,
    ) -> Dict[str, float]:
        return {
            action_key: (
                score_action(
                    subject_attributes,
                    action_attributes,
                    bandit_model.coefficients[action_key],
                )
                if action_key in bandit_model.coefficients
                else bandit_model.default_action_score
            )
            for action_key, action_attributes in actions.items()
        }

    def weigh_actions(
        self, action_scores, gamma, probability_floor
    ) -> Dict[str, float]:
        number_of_actions = len(action_scores)
        best_action = max(action_scores, key=action_scores.get)
        best_score = action_scores[best_action]

        # adjust probability floor for number of actions to control the sum
        min_probability = probability_floor / number_of_actions

        # weight all but the best action
        weights = {
            action_key: max(
                min_probability,
                1.0 / (number_of_actions + gamma * (best_score - score)),
            )
            for action_key, score in action_scores.items()
            if action_key != best_action
        }

        # remaining weight goes to best action
        remaining_weight = max(0.0, 1.0 - sum(weights.values()))
        weights[best_action] = remaining_weight
        return weights

    def select_action(self, flag_key, subject_key, action_weights) -> str:
        # deterministic ordering
        sorted_action_weights = sorted(
            action_weights.items(),
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

        for action_key, weight in sorted_action_weights:
            cumulative_weight += weight
            if cumulative_weight > shard_value:
                return action_key

        # If no action is selected, return the last action (fallback)
        raise BanditEvaluationError(
            f"[Eppo SDK] No action selected for {flag_key} {subject_key}"
        )


def score_action(
    subject_attributes: ContextAttributes,
    action_attributes: ContextAttributes,
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
