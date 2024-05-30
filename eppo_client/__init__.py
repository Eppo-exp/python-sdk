from typing import Optional
from eppo_client.client import EppoClient
from eppo_client.config import Config
from eppo_client.configuration_requestor import (
    ExperimentConfigurationRequestor,
)
from eppo_client.configuration_store import ConfigurationStore
from eppo_client.http_client import HttpClient, SdkParams
from eppo_client.models import BanditData, Flag
from eppo_client.read_write_lock import ReadWriteLock
from eppo_client.version import __version__


__client: Optional[EppoClient] = None
__lock = ReadWriteLock()


def init(config: Config) -> EppoClient:
    """Initializes a global Eppo client instance

    This method should be called once on application startup.
    If invoked more than once, it will re-initialize the global client instance.
    Use the :func:`eppo_client.get_instance()` method to access the client instance.

    :param config: client configuration containing the API Key
    :type config: Config
    """
    config._validate()
    sdk_params = SdkParams(
        apiKey=config.api_key, sdkName="python", sdkVersion=__version__
    )
    http_client = HttpClient(base_url=config.base_url, sdk_params=sdk_params)
    flag_config_store: ConfigurationStore[Flag] = ConfigurationStore()
    bandit_config_store: ConfigurationStore[BanditData] = ConfigurationStore()
    config_requestor = ExperimentConfigurationRequestor(
        http_client=http_client,
        flag_config_store=flag_config_store,
        bandit_config_store=bandit_config_store,
    )
    assignment_logger = config.assignment_logger
    is_graceful_mode = config.is_graceful_mode
    global __client
    global __lock
    with __lock.writer():
        if __client:
            # if a client was already initialized, stop the background processes of the old client
            __client._shutdown()
        __client = EppoClient(
            config_requestor=config_requestor,
            assignment_logger=assignment_logger,
            is_graceful_mode=is_graceful_mode,
        )
        return __client


def get_instance() -> EppoClient:
    """Used to access an initialized client instance

    Use this method to get a client instance for assigning variants.
    This method may only be called after invocation of :func:`eppo_client.init()`, otherwise it throws an exception.

    :return: a shared client instance
    :rtype: EppoClient
    """
    global __client
    global __lock
    with __lock.reader():
        if __client:
            return __client
        else:
            raise Exception("init() must be called before get_instance()")
