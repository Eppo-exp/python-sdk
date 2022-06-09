import numbers
import re
from enum import Enum
from tokenize import Number
from typing import List, Union

from eppo_client.base_model import SdkBaseModel


class OperatorType(Enum):
    MATCHES = "MATCHES"
    GTE = "GTE"
    GT = "GT"
    LTE = "LTE"
    LT = "LT"


class Condition(SdkBaseModel):
    operator: OperatorType
    attribute: str
    value: Union[int, float, str]


class Rule(SdkBaseModel):
    conditions: List[Condition]


def matches_any_rule(subject_attributes: dict, rules: List[Rule]):
    for rule in rules:
        if matches_rule(subject_attributes, rule):
            return True
    return False


def matches_rule(subject_attributes: dict, rule: Rule):
    for condition in rule.conditions:
        if not evaluate_condition(subject_attributes, condition):
            return False
    return True


def evaluate_condition(subject_attributes: dict, condition: Condition) -> bool:
    subject_value = subject_attributes.get(condition.attribute, None)
    if subject_value:
        if isinstance(subject_value, numbers.Number):
            return evaluate_numeric_condition(subject_value, condition)
        elif condition.operator == OperatorType.MATCHES:
            return bool(re.match(condition.value, subject_value))
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
