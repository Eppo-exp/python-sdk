from typing import Dict, List, Union

ValueType = Union[str, int, float, bool]
AttributeType = Union[str, int, float, bool, None]
ConditionValueType = Union[AttributeType, List[AttributeType]]
AttributesDict = Dict[str, AttributeType]
Action = str
