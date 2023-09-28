import json
from numbers import Number
from eppo_client.configuration_requestor import VariationDto


class VariationType:
    STRING = "string"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    JSON = "json"

    @classmethod
    def is_expected_type(
        cls, assigned_variation: VariationDto, expected_variation_type: str
    ) -> bool:
        if expected_variation_type == cls.STRING:
            return isinstance(assigned_variation.typedValue, str)
        elif expected_variation_type == cls.NUMERIC:
            return isinstance(assigned_variation.typedValue, Number) and not isinstance(assigned_variation.typedValue, bool)
        elif expected_variation_type == cls.BOOLEAN:
            return isinstance(assigned_variation.typedValue, bool)
        elif expected_variation_type == cls.JSON:
            try:
                parsed_json = json.loads(assigned_variation.value)
                json.dumps(assigned_variation.typedValue)
                return parsed_json == assigned_variation.typedValue
            except (json.JSONDecodeError, TypeError):
                pass
        return False
