from typing import Dict, List, Union

ValueType = Union[str, int, float, bool]
AttributeType = Union[str, int, float, bool]
ConditionValueType = Union[AttributeType, List[AttributeType]]
SubjectAttributes = Dict[str, AttributeType]
