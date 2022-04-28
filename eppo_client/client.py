from typing import Optional
from eppo_client.config import Config


class EppoClient:
    """
    The client should be initialized at application startup as a singleton; use the same client instance for the lifetime of the application.
    Use the :func:`eppo_client.get()` method to get a shared instance of the client.
    """

    def __init__(self, config: Config) -> None:
        """
        :param config: SDK configuration params including api key
        """
        config._validate()
        self.__config = config

    def assign(self, subject: str, flag: str) -> Optional[str]:
        """Maps a subject to a variation for a given experiment
        Returns None if the subject is not part of the experiment sample.

        :param subject: an entity ID, e.g. userId
        :param flag: an experiment identifier
        """
        return None
