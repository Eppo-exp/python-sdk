import eppo_client
from eppo_client.config import Config
from eppo_client.assignment_logger import AssignmentLogger


def test_no_poller():
    eppo_client.init(
        Config(
            api_key="blah",
            poll_interval_seconds=None,
            assignment_logger=AssignmentLogger(),
        )
    )
