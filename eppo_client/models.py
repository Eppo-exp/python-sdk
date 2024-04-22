from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from eppo_client.base_model import SdkBaseModel
from eppo_client.rules import Rule
from eppo_client.types import ValueType


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
