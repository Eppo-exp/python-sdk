from pydantic import ConfigDict, BaseModel
from pydantic.alias_generators import to_camel


class SdkBaseModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
