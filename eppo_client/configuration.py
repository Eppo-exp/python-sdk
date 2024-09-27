from typing import Union
from eppo_client.models import UfcResponse, BanditResponse


class Configuration:
    """
    Client configuration fetched from the backend that dictates how to
    interpret feature flags.
    """

    def __init__(
        self,
        flags_configuration: Union[bytes, str],
        bandits_configuration: Union[bytes, str, None] = None,
    ) -> None:
        self._flags_configuration = UfcResponse.model_validate_json(flags_configuration)

        self._bandits_configuration = None
        if bandits_configuration is not None:
            self._bandits_configuration = BanditResponse.model_validate_json(
                bandits_configuration
            )
