"""
Run using
`fastapi dev 03_bandit.py`

Test using
`curl "http://127.0.0.1:8000/bandit?name=bob&country=UK&age=25"`
"""

from dotenv import load_dotenv
import os

from fastapi import FastAPI
import eppo_client
from eppo_client.config import Config, AssignmentLogger
import eppo_client.bandit

load_dotenv()
EPPO_API_KEY = os.environ.get("EPPO_API_KEY")
print(EPPO_API_KEY[:5] + "...")

app = FastAPI()


class LocalLogger(AssignmentLogger):
    def log_assignment(self, assignment_event):
        print(assignment_event)

    def log_bandit_assignment(self, bandit_assignment):
        print(bandit_assignment)


client_config = Config(api_key=EPPO_API_KEY, assignment_logger=LocalLogger())

eppo_client.init(client_config)


@app.get("/bandit")
async def bandit(name: str, country: str, age: int):
    client = eppo_client.get_instance()

    print(client.get_flag_keys())

    bandit_result = client.get_bandit_action(
        "shoe-bandit",
        name,
        eppo_client.bandit.ContextAttributes(
            numeric_attributes={"age": age}, categorical_attributes={"country": country}
        ),
        {
            "nike": eppo_client.bandit.ContextAttributes(
                numeric_attributes={"brand_affinity": 2.3},
                categorical_attributes={"aspect_ratio": "16:9"},
            ),
            "adidas": eppo_client.bandit.ContextAttributes(
                numeric_attributes={"brand_affinity": 0.2},
                categorical_attributes={"aspect_ratio": "16:9"},
            ),
        },
        "control",
    )

    if bandit_result.action:
        return f"The bandit recommends {bandit_result.action} to {name}"

    return f"{name} was assigned to {bandit_result.variation}"
