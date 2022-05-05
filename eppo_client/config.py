from eppo_client.base_model import SdkBaseModel

from eppo_client.validation import validate_not_blank


class Config(SdkBaseModel):
    """Eppo client configurations.

    Pass this configuration object to the :func:`eppo_client.init()` method to generate a client instance.

    :param api_key: Eppo API Key
    :type api_key: str

    :param base_url: Base URL of the Eppo Experiments API. Clients should use the default setting in most cases.
    :type base_url: str
    """

    api_key: str
    base_url: str = "https://eppo.cloud/api"

    def _validate(self):
        validate_not_blank("api_key", self.api_key)
