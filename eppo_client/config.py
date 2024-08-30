from pydantic import Field, ConfigDict

from eppo_client.assignment_logger import AssignmentLogger
from eppo_client.base_model import SdkBaseModel
from eppo_client.validation import validate_not_blank
from eppo_client.constants import (
    POLL_INTERVAL_SECONDS_DEFAULT,
    POLL_JITTER_SECONDS_DEFAULT,
)


class Config(SdkBaseModel):
    model_config = ConfigDict(
        # AssignmentLogger is not a pydantic model
        arbitrary_types_allowed=True
    )

    api_key: str
    base_url: str = "https://fscdn.eppo.cloud/api"
    assignment_logger: AssignmentLogger = Field(exclude=True)
    is_graceful_mode: bool = True
    poll_interval_seconds: int = POLL_INTERVAL_SECONDS_DEFAULT
    poll_jitter_seconds: int = POLL_JITTER_SECONDS_DEFAULT

    def _validate(self):
        validate_not_blank("api_key", self.api_key)
