import numbers
import re
import semver
from enum import Enum
from typing import Any, List

from eppo_client.models import SdkBaseModel
from eppo_client.types import ConditionValueType, SubjectAttributes


class OperatorType(Enum):
    MATCHES = "MATCHES"
    NOT_MATCHES = "NOT_MATCHES"
    GTE = "GTE"
    GT = "GT"
    LTE = "LTE"
    LT = "LT"
    ONE_OF = "ONE_OF"
    NOT_ONE_OF = "NOT_ONE_OF"
    IS_NULL = "IS_NULL"


class Condition(SdkBaseModel):
    operator: OperatorType
    attribute: Any
    value: ConditionValueType


class Rule(SdkBaseModel):
    conditions: List[Condition]


def matches_rule(rule: Rule, subject_attributes: SubjectAttributes) -> bool:
    return all(
        evaluate_condition(condition, subject_attributes)
        for condition in rule.conditions
    )


def evaluate_condition(
    condition: Condition, subject_attributes: SubjectAttributes
) -> bool:
    subject_value = subject_attributes.get(condition.attribute, None)
    if condition.operator == OperatorType.IS_NULL:
        if condition.value:
            return subject_value is None
        return subject_value is not None

    if subject_value is not None:
        if condition.operator == OperatorType.MATCHES:
            return isinstance(condition.value, str) and bool(
                re.match(condition.value, str(subject_value))
            )
        if condition.operator == OperatorType.NOT_MATCHES:
            return isinstance(condition.value, str) and not bool(
                re.match(condition.value, str(subject_value))
            )
        elif condition.operator == OperatorType.ONE_OF:
            return isinstance(condition.value, list) and str(subject_value).lower() in [
                str(value).lower() for value in condition.value
            ]
        elif condition.operator == OperatorType.NOT_ONE_OF:
            return isinstance(condition.value, list) and str(
                subject_value
            ).lower() not in [str(value).lower() for value in condition.value]
        else:
            # Numeric operator: value could be numeric or semver.
            if isinstance(subject_value, numbers.Number):
                return evaluate_numeric_condition(subject_value, condition)
            elif isinstance(subject_value, str) and is_valid_semver(subject_value):
                return compare_semver(
                    subject_value, condition.value, condition.operator
                )
    return False


def evaluate_numeric_condition(
    subject_value: numbers.Number, condition: Condition
) -> bool:
    if not isinstance(condition.value, numbers.Number):
        # this ensures we are comparing numbers to numbers below
        # but mypy is not smart enough to tell, so we ignore types below
        return False
    elif condition.operator == OperatorType.GT:
        return subject_value > condition.value  # type: ignore
    elif condition.operator == OperatorType.GTE:
        return subject_value >= condition.value  # type: ignore
    elif condition.operator == OperatorType.LT:
        return subject_value < condition.value  # type: ignore
    elif condition.operator == OperatorType.LTE:
        return subject_value <= condition.value  # type: ignore

    return False


def is_valid_semver(value: str) -> bool:
    try:
        # Parse the string. If it's a valid semver, it will return without errors.
        semver.VersionInfo.parse(value)
        return True
    except ValueError:
        # If a ValueError is raised, the string is not a valid semver.
        return False


def compare_semver(
    attribute_value: Any, condition_value: Any, operator: OperatorType
) -> bool:
    if not is_valid_semver(attribute_value) or not is_valid_semver(condition_value):
        return False

    if operator == OperatorType.GT:
        return semver.compare(attribute_value, condition_value) > 0
    elif operator == OperatorType.GTE:
        return semver.compare(attribute_value, condition_value) >= 0
    elif operator == OperatorType.LT:
        return semver.compare(attribute_value, condition_value) < 0
    elif operator == OperatorType.LTE:
        return semver.compare(attribute_value, condition_value) <= 0

    return False
