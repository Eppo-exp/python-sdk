def validate_not_blank(field_name: str, field_value: str):
    if field_value is None or field_value == "":
        raise ValueError("Invalid value for {}: cannot be blank".format(field_name))
