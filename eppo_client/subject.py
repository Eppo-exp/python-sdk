from typing import Dict
from eppo_client.base_model import SdkBaseModel


class Subject(SdkBaseModel):
    key: str
    custom_attributes: Dict = dict()
