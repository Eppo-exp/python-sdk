from eppo_client.assignment_logger import AssignmentLogger
from eppo_client.base_model import SdkBaseModel

from eppo_client.validation import validate_not_blank


class Config(SdkBaseModel):
    api_key: str
    base_url: str = "https://fscdn.eppo.cloud/api"
    assignment_logger: AssignmentLogger

    def _validate(self):
        validate_not_blank("api_key", self.api_key)

    class Config:
        # needed for the AssignmentLogger class which is not of type SdkBaseModel
        arbitrary_types_allowed = True
