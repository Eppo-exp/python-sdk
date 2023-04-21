import logging
from typing import Any, Dict, List, Optional, cast
from eppo_client.base_model import SdkBaseModel
from eppo_client.configuration_store import ConfigurationStore
from eppo_client.http_client import HttpClient
from eppo_client.rules import Rule

from eppo_client.shard import ShardRange

logger = logging.getLogger(__name__)


class VariationDto(SdkBaseModel):
    name: str
    value: Any
    shard_range: ShardRange


class AllocationDto(SdkBaseModel):
    percent_exposure: float
    variations: List[VariationDto]


class ExperimentConfigurationDto(SdkBaseModel):
    subject_shards: int
    enabled: bool
    name: Optional[str]
    overrides: Dict[str, str] = {}
    rules: List[Rule] = []
    allocations: Dict[str, AllocationDto]


RAC_ENDPOINT = "/randomized_assignment/v3/config"


class ExperimentConfigurationRequestor:
    def __init__(
        self,
        http_client: HttpClient,
        config_store: ConfigurationStore[ExperimentConfigurationDto],
    ):
        self.__http_client = http_client
        self.__config_store = config_store

    def get_configuration(
        self, experiment_key: str
    ) -> Optional[ExperimentConfigurationDto]:
        if self.__http_client.is_unauthorized():
            raise ValueError("Unauthorized: please check your API key")
        return self.__config_store.get_configuration(experiment_key)

    def fetch_and_store_configurations(self) -> Dict[str, ExperimentConfigurationDto]:
        try:
            configs = cast(dict, self.__http_client.get(RAC_ENDPOINT).get("flags", {}))
            for exp_key, exp_config in configs.items():
                configs[exp_key] = ExperimentConfigurationDto(**exp_config)
            self.__config_store.set_configurations(configs)
            return configs
        except Exception as e:
            logger.error("Error retrieving assignment configurations: " + str(e))
            return {}
