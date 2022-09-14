import numbers
import re
from enum import Enum
from typing import Any, List

from eppo_client.base_model import SdkBaseModel


class OperatorType(Enum):
    MATCHES = "MATCHES"
    GTE = "GTE"
    GT = "GT"
    LTE = "LTE"
    LT = "LT"
    ONE_OF = "ONE_OF"
    NOT_ONE_OF = "NOT_ONE_OF"


class Condition(SdkBaseModel):
    operator: OperatorType
    attribute: str
    value: Any


class Rule(SdkBaseModel):
    allocation_key: str
    conditions: List[Condition]


def find_matching_rule(subject_attributes: dict, rules: List[Rule]):
    for rule in rules:
        if matches_rule(subject_attributes, rule):
            return rule
    return None


def matches_rule(subject_attributes: dict, rule: Rule):
    for condition in rule.conditions:
        if not evaluate_condition(subject_attributes, condition):
            return False
    return True


def evaluate_condition(subject_attributes: dict, condition: Condition) -> bool:
    subject_value = subject_attributes.get(condition.attribute, None)
    if subject_value is not None:
        if condition.operator == OperatorType.MATCHES:
            return bool(re.match(condition.value, str(subject_value)))
        elif condition.operator == OperatorType.ONE_OF:
            return str(subject_value).lower() in [
                value.lower() for value in condition.value
            ]
        elif condition.operator == OperatorType.NOT_ONE_OF:
            return str(subject_value).lower() not in [
                value.lower() for value in condition.value
            ]
        else:
            return isinstance(
                subject_value, numbers.Number
            ) and evaluate_numeric_condition(subject_value, condition)
    return False


def evaluate_numeric_condition(subject_value: numbers.Number, condition: Condition):
    if condition.operator == OperatorType.GT:
        return subject_value > condition.value
    elif condition.operator == OperatorType.GTE:
        return subject_value >= condition.value
    elif condition.operator == OperatorType.LT:
        return subject_value < condition.value
    elif condition.operator == OperatorType.LTE:
        return subject_value <= condition.value
    return False
