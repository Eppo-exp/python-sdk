import pytest
from eppo_client.client import EppoClient
from eppo_client.config import Config


def test_blank_api_key():
    with pytest.raises(Exception) as exc_info:
        config = Config("")
        EppoClient(config=config)
    assert exc_info.value.args[0] == "Invalid configuration: api_key is required"
