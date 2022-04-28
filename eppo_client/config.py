from typing import Optional


class Config:
    """
    Configurations passed to :func:`eppo_client.set_config()` to initialize a client instance.
    """

    def __init__(self, api_key: str, base_url: str = "https://eppo.cloud/api"):
        """
        :param api_key: Eppo API key
        :param base_url: Base URL of the Eppo API. Clients should use the default setting in most cases.
        """
        self.__api_key = api_key
        self.__base_url = base_url

    @property
    def api_key(self) -> Optional[str]:
        return self.__api_key

    @property
    def base_url(self) -> str:
        return self.__base_url

    def _validate(self):
        if self.api_key is None or self.api_key == "":
            raise ValueError("Invalid configuration: api_key is required")
