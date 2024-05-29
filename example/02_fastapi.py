"""
Run using
`fastapi dev 02_fastapi.py`

Test using
`curl "http://127.0.0.1:8000/hello?name=bob"`
"""

from dotenv import load_dotenv
import os

from fastapi import FastAPI
import eppo_client
from eppo_client.config import Config, AssignmentLogger

load_dotenv()
EPPO_API_KEY = os.environ.get("EPPO_API_KEY")
print(EPPO_API_KEY[:5] + "...")

app = FastAPI()


class LocalLogger(AssignmentLogger):
    def log_assignment(self, assignment_event):
        print(assignment_event)


client_config = Config(api_key=EPPO_API_KEY, assignment_logger=LocalLogger())

eppo_client.init(client_config)


@app.get("/hello")
async def hello(name: str):
    client = eppo_client.get_instance()

    print(client.get_flag_keys())
    greeting = client.get_string_assignment("hello-world-greeting", name, {}, "Hello")

    return f"{greeting}, {name}!"
