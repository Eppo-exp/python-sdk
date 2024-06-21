import logging
from typing import Dict, Optional, cast
from eppo_client.configuration_store import ConfigurationStore
from eppo_client.http_client import HttpClient
from eppo_client.models import BanditData, Flag

logger = logging.getLogger(__name__)


UFC_ENDPOINT = "/flag-config/v1/config"
BANDIT_ENDPOINT = "/flag-config/v1/bandits"


class ExperimentConfigurationRequestor:
    def __init__(
        self,
        http_client: HttpClient,
        flag_config_store: ConfigurationStore[Flag],
        bandit_config_store: ConfigurationStore[BanditData],
    ):
        self.__http_client = http_client
        self.__flag_config_store = flag_config_store
        self.__bandit_config_store = bandit_config_store
        self.__is_initialized = False

    def get_configuration(self, flag_key: str) -> Optional[Flag]:
        if self.__http_client.is_unauthorized():
            raise ValueError("Unauthorized: please check your API key")
        return self.__flag_config_store.get_configuration(flag_key)

    def get_bandit_model(self, bandit_key: str) -> Optional[BanditData]:
        if self.__http_client.is_unauthorized():
            raise ValueError("Unauthorized: please check your API key")
        return self.__bandit_config_store.get_configuration(bandit_key)

    def get_flag_keys(self):
        return self.__flag_config_store.get_keys()

    def get_flag_configurations(self):
        return self.__flag_config_store.get_configurations()

    def get_bandit_keys(self):
        return self.__bandit_config_store.get_keys()

    def fetch_flags(self):
        return self.__http_client.get(UFC_ENDPOINT)

    def fetch_bandits(self):
        return self.__http_client.get(BANDIT_ENDPOINT)

    def store_flags(self, flag_data) -> Dict[str, Flag]:
        flag_config_dict = cast(dict, flag_data.get("flags", {}))
        flag_configs = {key: Flag(**config) for key, config in flag_config_dict.items()}
        self.__flag_config_store.set_configurations(flag_configs)
        return flag_configs

    def store_bandits(self, bandit_data) -> Dict[str, BanditData]:
        bandit_configs = {
            key: BanditData(**data)
            for key, data in cast(dict, bandit_data.get("bandits", {})).items()
        }
        self.__bandit_config_store.set_configurations(bandit_configs)
        return bandit_configs

    def fetch_and_store_configurations(self):
        try:
            flag_data = self.fetch_flags()
            self.store_flags(flag_data)

            if flag_data.get("bandits", {}):
                bandit_data = self.fetch_bandits()
                self.store_bandits(bandit_data)
            self.__is_initialized = True
        except Exception as e:
            logger.error("Error retrieving configurations: " + str(e))

    def is_initialized(self):
        return self.__is_initialized
