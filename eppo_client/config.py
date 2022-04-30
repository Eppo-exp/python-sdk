from dataclasses import dataclass

from eppo_client.validation import validate_not_blank


@dataclass
class Config:
    api_key: str
    base_url: str = "https://eppo.cloud/api"

    def _validate(self):
        validate_not_blank("api_key", self.api_key)
