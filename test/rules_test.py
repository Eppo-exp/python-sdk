from eppo_client.rules import (
    OperatorType,
    Rule,
    Condition,
    evaluate_condition,
    matches_rule,
    to_string,
)

greater_than_condition = Condition(operator=OperatorType.GT, value=10, attribute="age")
less_than_condition = Condition(operator=OperatorType.LT, value=100, attribute="age")
numeric_rule = Rule(
    conditions=[less_than_condition, greater_than_condition],
)

matches_email_condition = Condition(
    operator=OperatorType.MATCHES, value=".*@email.com", attribute="email"
)
text_rule = Rule(conditions=[matches_email_condition])

rule_with_empty_conditions = Rule(conditions=[])


def test_matches_rule_with_empty_rule():
    assert matches_rule(Rule(conditions=[]), {})


def test_matches_rule_with_single_condition():
    assert matches_rule(
        Rule(
            conditions=[Condition(operator=OperatorType.GT, value=10, attribute="age")]
        ),
        {"age": 11},
    )


def test_matches_rule_with_single_condition_missing_attribute():
    assert not matches_rule(
        Rule(
            conditions=[Condition(operator=OperatorType.GT, value=10, attribute="age")]
        ),
        {"name": "alice"},
    )


def test_matches_rule_with_single_false_condition():
    assert not matches_rule(
        Rule(
            conditions=[Condition(operator=OperatorType.GT, value=10, attribute="age")]
        ),
        {"age": 9},
    )


def test_matches_rule_with_two_conditions():
    assert matches_rule(
        Rule(
            conditions=[
                Condition(operator=OperatorType.GT, value=10, attribute="age"),
                Condition(operator=OperatorType.LT, value=100, attribute="age"),
            ]
        ),
        {"age": 20},
    )


def test_matches_rule_with_true_and_false_condition():
    assert not matches_rule(
        Rule(
            conditions=[
                Condition(operator=OperatorType.GT, value=10, attribute="age"),
                Condition(operator=OperatorType.LT, value=20, attribute="age"),
            ]
        ),
        {"age": 30},
    )


def test_evaluate_condition_one_of():
    assert evaluate_condition(
        Condition(
            operator=OperatorType.ONE_OF, value=["alice", "bob"], attribute="name"
        ),
        {"name": "alice"},
    )
    assert evaluate_condition(
        Condition(
            operator=OperatorType.ONE_OF, value=["alice", "bob"], attribute="name"
        ),
        {"name": "bob"},
    )
    assert not evaluate_condition(
        Condition(
            operator=OperatorType.ONE_OF, value=["alice", "bob"], attribute="name"
        ),
        {"name": "charlie"},
    )


def test_evaluate_condition_not_one_of():
    assert not evaluate_condition(
        Condition(
            operator=OperatorType.NOT_ONE_OF, value=["alice", "bob"], attribute="name"
        ),
        {"name": "alice"},
    )
    assert not evaluate_condition(
        Condition(
            operator=OperatorType.NOT_ONE_OF, value=["alice", "bob"], attribute="name"
        ),
        {"name": "bob"},
    )
    assert evaluate_condition(
        Condition(
            operator=OperatorType.NOT_ONE_OF, value=["alice", "bob"], attribute="name"
        ),
        {"name": "charlie"},
    )

    # NOT_ONE_OF fails when attribute is not specified
    assert not evaluate_condition(
        Condition(
            operator=OperatorType.NOT_ONE_OF, value=["alice", "bob"], attribute="name"
        ),
        {},
    )

    assert not evaluate_condition(
        Condition(
            operator=OperatorType.NOT_ONE_OF, value=["alice", "bob"], attribute="name"
        ),
        {"name": None},
    )


def test_evaluate_condition_matches():
    assert evaluate_condition(
        Condition(operator=OperatorType.MATCHES, value="^test.*", attribute="email"),
        {"email": "test@example.com"},
    )
    assert evaluate_condition(
        Condition(operator=OperatorType.MATCHES, value="true", attribute="flag"),
        {"flag": True},
    )
    assert evaluate_condition(
        Condition(operator=OperatorType.MATCHES, value="false", attribute="flag"),
        {"flag": False},
    )
    assert not evaluate_condition(
        Condition(operator=OperatorType.MATCHES, value="^test.*", attribute="email"),
        {"email": "example@test.com"},
    )
    assert not evaluate_condition(
        Condition(operator=OperatorType.MATCHES, value="False", attribute="flag"),
        {"flag": False},
    )


def test_evaluate_condition_matches_partial():
    assert evaluate_condition(
        Condition(
            operator=OperatorType.MATCHES, value="@example\\.com", attribute="email"
        ),
        {"email": "alice@example.com"},
    )
    assert not evaluate_condition(
        Condition(
            operator=OperatorType.MATCHES, value="@example\\.com", attribute="email"
        ),
        {"email": "alice@sample.com"},
    )
    assert evaluate_condition(
        Condition(
            operator=OperatorType.MATCHES, value="@example\\.com", attribute="email"
        ),
        {"email": "bob@example.com"},
    )


def test_evaluate_condition_not_matches():
    assert not evaluate_condition(
        Condition(
            operator=OperatorType.NOT_MATCHES, value="^test.*", attribute="email"
        ),
        {"email": "test@example.com"},
    )
    assert not evaluate_condition(
        Condition(
            operator=OperatorType.NOT_MATCHES, value="^test.*", attribute="email"
        ),
        {},
    )
    assert evaluate_condition(
        Condition(
            operator=OperatorType.NOT_MATCHES, value="^test.*", attribute="email"
        ),
        {"email": "example@test.com"},
    )


def test_evaluate_condition_gte():
    assert evaluate_condition(
        Condition(operator=OperatorType.GTE, value=18, attribute="age"),
        {"age": 18},
    )
    assert not evaluate_condition(
        Condition(operator=OperatorType.GTE, value=18, attribute="age"),
        {"age": 17},
    )


def test_evaluate_condition_gt():
    assert evaluate_condition(
        Condition(operator=OperatorType.GT, value=18, attribute="age"),
        {"age": 19},
    )
    assert not evaluate_condition(
        Condition(operator=OperatorType.GT, value=18, attribute="age"),
        {"age": 18},
    )


def test_evaluate_condition_lte():
    assert evaluate_condition(
        Condition(operator=OperatorType.LTE, value=18, attribute="age"),
        {"age": 18},
    )
    assert not evaluate_condition(
        Condition(operator=OperatorType.LTE, value=18, attribute="age"),
        {"age": 19},
    )


def test_evaluate_condition_lt():
    assert evaluate_condition(
        Condition(operator=OperatorType.LT, value=18, attribute="age"),
        {"age": 17},
    )
    assert not evaluate_condition(
        Condition(operator=OperatorType.LT, value=18, attribute="age"),
        {"age": 18},
    )


def test_evaluate_condition_semver_gte():
    assert evaluate_condition(
        Condition(operator=OperatorType.GTE, value="1.0.0", attribute="version"),
        {"version": "1.0.1"},
    )

    assert evaluate_condition(
        Condition(operator=OperatorType.GTE, value="1.0.0", attribute="version"),
        {"version": "1.0.0"},
    )

    assert not evaluate_condition(
        Condition(operator=OperatorType.GTE, value="1.10.0", attribute="version"),
        {"version": "1.2.0"},
    )

    assert evaluate_condition(
        Condition(operator=OperatorType.GTE, value="1.5.0", attribute="version"),
        {"version": "1.13.0"},
    )

    assert not evaluate_condition(
        Condition(operator=OperatorType.GTE, value="1.0.0", attribute="version"),
        {"version": "0.9.9"},
    )


def test_evaluate_condition_semver_gt():
    assert evaluate_condition(
        Condition(operator=OperatorType.GT, value="1.0.0", attribute="version"),
        {"version": "1.0.1"},
    )

    assert not evaluate_condition(
        Condition(operator=OperatorType.GT, value="1.0.0", attribute="version"),
        {"version": "1.0.0"},
    )

    assert not evaluate_condition(
        Condition(operator=OperatorType.GT, value="1.10.0", attribute="version"),
        {"version": "1.2.903"},
    )

    assert evaluate_condition(
        Condition(operator=OperatorType.GT, value="1.5.0", attribute="version"),
        {"version": "1.13.0"},
    )

    assert not evaluate_condition(
        Condition(operator=OperatorType.GT, value="1.0.0", attribute="version"),
        {"version": "0.9.9"},
    )


def test_evaluate_condition_semver_lte():
    assert not evaluate_condition(
        Condition(operator=OperatorType.LTE, value="1.0.0", attribute="version"),
        {"version": "1.0.1"},
    )

    assert evaluate_condition(
        Condition(operator=OperatorType.LTE, value="1.0.0", attribute="version"),
        {"version": "1.0.0"},
    )

    assert evaluate_condition(
        Condition(operator=OperatorType.LTE, value="1.10.0", attribute="version"),
        {"version": "1.2.0"},
    )

    assert not evaluate_condition(
        Condition(operator=OperatorType.LTE, value="1.5.0", attribute="version"),
        {"version": "1.13.0"},
    )

    assert evaluate_condition(
        Condition(operator=OperatorType.LTE, value="1.0.0", attribute="version"),
        {"version": "0.9.9"},
    )


def test_evaluate_condition_semver_lt():
    assert not evaluate_condition(
        Condition(operator=OperatorType.LT, value="1.0.0", attribute="version"),
        {"version": "1.0.1"},
    )

    assert not evaluate_condition(
        Condition(operator=OperatorType.LT, value="1.0.0", attribute="version"),
        {"version": "1.0.0"},
    )

    assert evaluate_condition(
        Condition(operator=OperatorType.LT, value="1.10.0", attribute="version"),
        {"version": "1.2.0"},
    )

    assert not evaluate_condition(
        Condition(operator=OperatorType.LT, value="1.5.0", attribute="version"),
        {"version": "1.13.0"},
    )

    assert evaluate_condition(
        Condition(operator=OperatorType.LT, value="1.0.0", attribute="version"),
        {"version": "0.9.9"},
    )


def test_evaluate_condition_one_of_int():
    one_of_condition_int = Condition(
        operator=OperatorType.ONE_OF, value=[10, 20, 30], attribute="number"
    )
    assert evaluate_condition(one_of_condition_int, {"number": 20})
    assert not evaluate_condition(one_of_condition_int, {"number": 40})
    assert not evaluate_condition(one_of_condition_int, {})


def test_evaluate_condition_one_of_boolean():
    one_of_condition_boolean = Condition(
        operator=OperatorType.ONE_OF, value=["true", "false"], attribute="status"
    )
    assert evaluate_condition(one_of_condition_boolean, {"status": False})
    assert evaluate_condition(one_of_condition_boolean, {"status": "false"})
    assert not evaluate_condition(one_of_condition_boolean, {"status": "Maybe"})
    assert not evaluate_condition(one_of_condition_boolean, {"status": 0})
    assert not evaluate_condition(one_of_condition_boolean, {"status": 1})
    assert not evaluate_condition(one_of_condition_boolean, {})


def test_one_of_operator_with_number():
    one_of_condition = Condition(
        operator=OperatorType.ONE_OF, value=["14", "15.11"], attribute="number"
    )
    not_one_of_condition = Condition(
        operator=OperatorType.NOT_ONE_OF, value=["10"], attribute="number"
    )
    assert evaluate_condition(one_of_condition, {"number": "14"})
    assert evaluate_condition(one_of_condition, {"number": 14})
    assert not evaluate_condition(one_of_condition, {"number": 10})
    assert not evaluate_condition(one_of_condition, {"number": "10"})
    assert not evaluate_condition(not_one_of_condition, {"number": "10"})
    assert not evaluate_condition(not_one_of_condition, {"number": 10})
    assert evaluate_condition(not_one_of_condition, {"number": "11"})
    assert evaluate_condition(not_one_of_condition, {"number": 11})


def test_is_null_operator():
    is_null_condition = Condition(
        operator=OperatorType.IS_NULL, value=True, attribute="size"
    )
    assert evaluate_condition(is_null_condition, {"size": None})
    assert not evaluate_condition(is_null_condition, {"size": 10})
    assert evaluate_condition(is_null_condition, {})


def test_is_not_null_operator():
    is_not_null_condition = Condition(
        operator=OperatorType.IS_NULL, value=False, attribute="size"
    )
    assert not evaluate_condition(is_not_null_condition, {"size": None})
    assert evaluate_condition(is_not_null_condition, {"size": 10})
    assert not evaluate_condition(is_not_null_condition, {})


def test_to_string_string():
    assert to_string("test") == "test"


def test_to_string_int():
    assert to_string(10) == "10"


def test_to_string_float():
    assert to_string(10.5) == "10.5"
    assert to_string(10.0) == "10"
    assert to_string(123456789.0) == "123456789"


def test_to_string_bool():
    assert to_string(True) == "true"
    assert to_string(False) == "false"


def test_to_string_null():
    assert to_string(None) == "null"
