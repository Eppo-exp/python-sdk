from typing import Optional
from eppo_client.client import EppoClient
from eppo_client.config import Config
from eppo_client.configuration_requestor import (
    ExperimentConfigurationDto,
    ExperimentConfigurationRequestor,
)
from eppo_client.configuration_store import ConfigurationStore
from eppo_client.constants import MAX_CACHE_ENTRIES
from eppo_client.http_client import HttpClient, SdkParams
from eppo_client.read_write_lock import ReadWriteLock

__version__ = "1.2.1"

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
    config_store: ConfigurationStore[ExperimentConfigurationDto] = ConfigurationStore(
        max_size=MAX_CACHE_ENTRIES
    )
    config_requestor = ExperimentConfigurationRequestor(
        http_client=http_client, config_store=config_store
    )
    assignment_logger = config.assignment_logger
    global __client
    global __lock
    try:
        __lock.acquire_write()
        if __client:
            # if a client was already initialized, stop the background processes of the old client
            __client._shutdown()
        __client = EppoClient(
            config_requestor=config_requestor,
            assignment_logger=assignment_logger,
        )
        return __client
    finally:
        __lock.release_write()


def get_instance() -> EppoClient:
    """Used to access an initialized client instance

    Use this method to get a client instance for assigning variants.
    This method may only be called after invocation of :func:`eppo_client.init()`, otherwise it throws an exception.

    :return: a shared client instance
    :rtype: EppoClient
    """
    global __client
    global __lock
    try:
        __lock.acquire_read()
        if __client:
            return __client
        else:
            raise Exception("init() must be called before get_instance()")
    finally:
        __lock.release_read()
