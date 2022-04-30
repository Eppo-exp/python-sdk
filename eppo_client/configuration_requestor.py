from dataclasses import dataclass
import json

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
    variations: list[VariationDto]
    name: str

    @staticmethod
    def from_json(json_str: str):
        json_dict = json.load(json_str)
        variations = [
            VariationDto.from_dict(variation_dict)
            for variation_dict in json_dict["variations"]
        ]
        json_dict["variations"] = variations
        return ExperimentConfigurationDto(**json_dict)


class ExperimentConfigurationRequestor:
    def get_configuration(flag: str) -> ExperimentConfigurationDto:
        # TODO: implement this method
        return None
