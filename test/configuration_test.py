import pytest
import pydantic

from eppo_client.configuration import Configuration


def test_init_valid():
    Configuration(flags_configuration='{"flags": {}}')


def test_init_invalid_json():
    with pytest.raises(pydantic.ValidationError):
        Configuration(flags_configuration="")


def test_init_invalid_format():
    with pytest.raises(pydantic.ValidationError):
        Configuration(flags_configuration='{"flags": []}')
