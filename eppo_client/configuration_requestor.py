import logging
from typing import Dict, Optional, cast
from eppo_client.configuration_store import ConfigurationStore
from eppo_client.http_client import HttpClient
from eppo_client.models import Flag

logger = logging.getLogger(__name__)


UFC_ENDPOINT = "/flag-config/v1/config"


class ExperimentConfigurationRequestor:
    def __init__(
        self,
        http_client: HttpClient,
        config_store: ConfigurationStore[Flag],
    ):
        self.__http_client = http_client
        self.__config_store = config_store
        self.__is_initialized = False

    def get_configuration(self, flag_key: str) -> Optional[Flag]:
        if self.__http_client.is_unauthorized():
            raise ValueError("Unauthorized: please check your API key")
        return self.__config_store.get_configuration(flag_key)

    def get_flag_keys(self):
        return self.__config_store.get_keys()

    def fetch_and_store_configurations(self) -> Dict[str, Flag]:
        try:
            configs_dict = cast(
                dict, self.__http_client.get(UFC_ENDPOINT).get("flags", {})
            )
            configs = {key: Flag(**config) for key, config in configs_dict.items()}
            self.__config_store.set_configurations(configs)
            self.__is_initialized = True
            return configs
        except Exception as e:
            logger.error("Error retrieving flag configurations: " + str(e))
            return {}

    def is_initialized(self):
        return self.__is_initialized
