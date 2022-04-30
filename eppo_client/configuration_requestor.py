from dataclasses import dataclass
from typing import List, Optional

from eppo_client.shard import ShardRange


@dataclass
class VariationDto:
    name: str
    shardRange: ShardRange

    @staticmethod
    def from_dict(variation_dict):
        variation_dict["shardRange"] = ShardRange.from_dict(
            variation_dict["shardRange"]
        )
        return VariationDto(**variation_dict)


@dataclass
class ExperimentConfigurationDto:
    subjectShards: int
    percentExposure: float
    enabled: bool
    variations: List[VariationDto]
    name: str


class ExperimentConfigurationRequestor:
    def get_configuration(self, flag: str) -> Optional[ExperimentConfigurationDto]:
        # TODO: implement this method
        return None
