from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from eppo_client.base_model import SdkBaseModel
from eppo_client.rules import Rule
from eppo_client.types import Action, ValueType


class VariationType(Enum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    NUMERIC = "NUMERIC"
    BOOLEAN = "BOOLEAN"
    JSON = "JSON"


class Variation(SdkBaseModel):
    key: str
    value: ValueType


class Range(SdkBaseModel):
    start: int
    end: int


class Shard(SdkBaseModel):
    salt: str
    ranges: List[Range]


class Split(SdkBaseModel):
    shards: List[Shard]
    variation_key: str
    extra_logging: Dict[str, str] = {}


class Allocation(SdkBaseModel):
    key: str
    rules: List[Rule] = []
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    splits: List[Split]
    do_log: bool = True


class Flag(SdkBaseModel):
    key: str
    enabled: bool
    variation_type: VariationType
    variations: Dict[str, Variation]
    allocations: List[Allocation]
    total_shards: int = 10_000


class BanditVariation(SdkBaseModel):
    key: str
    flag_key: str
    variation_key: str
    variation_value: str


class BanditNumericAttributeCoefficient(SdkBaseModel):
    attribute_key: str
    coefficient: float
    missing_value_coefficient: float


class ValueCoefficient(SdkBaseModel):
    value: str
    coefficient: float


class BanditCategoricalAttributeCoefficient(SdkBaseModel):
    attribute_key: str
    missing_value_coefficient: float
    value_coefficients: Dict[str, float]


class BanditCoefficients(SdkBaseModel):
    action_key: str
    intercept: float
    subject_numeric_coefficients: List[BanditNumericAttributeCoefficient]
    subject_categorical_coefficients: List[BanditCategoricalAttributeCoefficient]
    action_numeric_coefficients: List[BanditNumericAttributeCoefficient]
    action_categorical_coefficients: List[BanditCategoricalAttributeCoefficient]


class BanditModelData(SdkBaseModel):
    gamma: float
    default_action_score: float
    action_probability_floor: float
    coefficients: Dict[Action, BanditCoefficients]


class BanditData(SdkBaseModel):
    bandit_key: str
    model_name: str
    updated_at: datetime
    model_version: str
    model_data: BanditModelData
