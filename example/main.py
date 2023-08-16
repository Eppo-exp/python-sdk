import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import eppo_client  # noqa
from eppo_client.config import Config  # noqa
from eppo_client.assignment_logger import AssignmentLogger  # noqa

API_KEY = "REPLACE WITH YOUR API KEY"


class ExampleAssignmentLogger(AssignmentLogger):
    def log_assignment(self, assignment):
        print(
            f'{assignment["subject"]} assigned {assignment["variation"]} for key {assignment["experiment"]}'
        )


def init_eppo_and_assign():
    client_config = Config(api_key=API_KEY, assignment_logger=ExampleAssignmentLogger())
    eppo_client.init(client_config)

    eppo = eppo_client.get_instance()

    # ensure the client is initialized before assigning
    time.sleep(1)

    subject = "user_1234"
    flag_key = "my-flag-key"

    assigned_variation = eppo.get_assignment(subject, flag_key)
    if assigned_variation == "control":
        print("Assigned to control")
    elif assigned_variation == "treatment":
        print("Assigned to treatment")
    else:
        print(f"Assigned unknown variation: {assigned_variation}")


if __name__ == "__main__":
    init_eppo_and_assign()
