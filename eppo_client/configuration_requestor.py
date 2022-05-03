from typing import List, Optional
from eppo_client.base_model import SdkBaseModel

from eppo_client.shard import ShardRange


class VariationDto(SdkBaseModel):
    name: str
    shard_range: ShardRange


class ExperimentConfigurationDto(SdkBaseModel):
    subject_shards: int
    percent_exposure: float
    enabled: bool
    variations: List[VariationDto]
    name: str


class ExperimentConfigurationRequestor:
    def get_configuration(self, flag: str) -> Optional[ExperimentConfigurationDto]:
        # TODO: implement this method
        return None
