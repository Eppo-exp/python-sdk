import eppo_client
import pytest

from eppo_client.config import Config
from eppo_client.configuration import Configuration
from eppo_client.assignment_logger import AssignmentLogger


def test_without_initial_configuration():
    client = eppo_client.init(
        Config(
            api_key="test",
            base_url="http://localhost:8378/api",
            assignment_logger=AssignmentLogger(),
        )
    )
    assert not client.is_initialized()


def test_with_initial_configuration():
    client = eppo_client.init(
        Config(
            api_key="test",
            base_url="http://localhost:8378/api",
            assignment_logger=AssignmentLogger(),
            initial_configuration=Configuration(flags_configuration='{"flags":{}}'),
        )
    )
    assert client.is_initialized()


def test_update_configuration():
    client = eppo_client.init(
        Config(
            api_key="test",
            poll_interval_seconds=None,
            assignment_logger=AssignmentLogger(),
        )
    )

    client.set_configuration(Configuration(flags_configuration='{"flags":{}}'))

    assert client.is_initialized()

def test_polling_interval_less_than_jitter():
    with pytest.raises(ValueError, match="poll_interval_seconds must be greater than poll_jitter_seconds"):
        eppo_client.init(
            Config(
                api_key="test",
                poll_interval_seconds=5,
                poll_jitter_seconds=10,
                assignment_logger=AssignmentLogger(),
            )
        )
