from typing import List, Union, Dict

ValueType = Union[str, int, float, bool]
AttributeType = Union[str, int, float, bool]
ConditionValueType = Union[AttributeType, List[AttributeType]]
SubjectAttributes = Dict[str, AttributeType]
