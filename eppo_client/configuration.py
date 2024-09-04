from eppo_client.models import UfcResponse


class Configuration:
    """
    Client configuration fetched from the backend that dictates how to
    interpret feature flags.
    """

    def __init__(self, flags_configuration: str):
        self._flags_configuration = UfcResponse.model_validate_json(flags_configuration)
