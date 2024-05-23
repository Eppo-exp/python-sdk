from typing import Dict
from eppo_client.base_model import BaseModel
from pydantic import ConfigDict


class AssignmentLogger(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def log_assignment(self, assignment_event: Dict):
        pass

    def log_bandit_action(self, bandit_event: Dict):
        pass
