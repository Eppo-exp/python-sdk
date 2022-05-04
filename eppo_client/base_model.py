from pydantic import BaseModel


def to_camel(s: str):
    words = s.split("_")
    if len(words) > 1:
        return words[0] + "".join([w.capitalize() for w in words[1:]])
    return words[0]


class SdkBaseModel(BaseModel):
    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True
