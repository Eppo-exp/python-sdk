from eppo_client.rules import (
    OperatorType,
    Rule,
    Condition,
    evaluate_condition,
    matches_rule,
)

greater_than_condition = Condition(operator=OperatorType.GT, value=10, attribute="age")
less_than_condition = Condition(operator=OperatorType.LT, value=100, attribute="age")
numeric_rule = Rule(
    allocation_key="allocation",
    conditions=[less_than_condition, greater_than_condition],
)

matches_email_condition = Condition(
    operator=OperatorType.MATCHES, value=".*@email.com", attribute="email"
)
text_rule = Rule(allocation_key="allocation", conditions=[matches_email_condition])

rule_with_empty_conditions = Rule(allocation_key="allocation", conditions=[])


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


def test_evaluate_condition_matches():
    assert evaluate_condition(
        Condition(operator=OperatorType.MATCHES, value=".*", attribute="name"),
        {"name": "alice"},
    )


def test_evaluate_condition_matches_false():
    assert not evaluate_condition(
        Condition(operator=OperatorType.MATCHES, value="bob", attribute="name"),
        {"name": "alice"},
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


# def test_find_matching_rule_with_empty_rules():
#     subject_attributes = {"age": 20, "country": "US"}
#     assert find_matching_rule([], "alice", subject_attributes) is None


# def test_find_matching_rule_when_no_rules_match():
#     subject_attributes = {"age": 99, "country": "US", "email": "test@example.com"}
#     assert find_matching_rule([text_rule], "alice", subject_attributes) is None


# def test_find_matching_rule_on_match():
#     assert find_matching_rule([numeric_rule], "alice", {"age": 99}) == numeric_rule
#     assert (
#         find_matching_rule([text_rule], "alice", {"email": "testing@email.com"})
#         == text_rule
#     )


# def test_find_matching_rule_if_no_attribute_for_condition():
#     assert find_matching_rule([numeric_rule], "alice", {}) is None


# def test_find_matching_rule_if_no_conditions_for_rule():
#     assert (
#         find_matching_rule([rule_with_empty_conditions], "alice", {})
#         == rule_with_empty_conditions
#     )


# def test_find_matching_rule_if_numeric_operator_with_string():
#     assert find_matching_rule([numeric_rule], "alice", {"age": "99"}) is None


# def test_find_matching_rule_with_numeric_value_and_regex():
#     condition = Condition(
#         operator=OperatorType.MATCHES, value="[0-9]+", attribute="age"
#     )
#     rule = Rule(conditions=[condition], allocation_key="allocation")
#     assert find_matching_rule([rule], "alice", {"age": 99}) == rule


# def test_find_matching_rule_with_semver():
#     semver_greater_than_condition = Condition(
#         operator=OperatorType.GTE, value="1.0.0", attribute="version"
#     )
#     semver_less_than_condition = Condition(
#         operator=OperatorType.LTE, value="2.0.0", attribute="version"
#     )
#     semver_rule = Rule(
#         allocation_key="allocation",
#         conditions=[semver_less_than_condition, semver_greater_than_condition],
#     )

#     assert find_matching_rule({"version": "1.1.0"}, [semver_rule]) is semver_rule
#     assert find_matching_rule({"version": "2.0.0"}, [semver_rule]) is semver_rule
#     assert find_matching_rule({"version": "2.1.0"}, [semver_rule]) is None


# def test_one_of_operator_with_boolean():
#     oneOfRule = Rule(
#         allocation_key="allocation",
#         conditions=[
#             Condition(operator=OperatorType.ONE_OF, value=["True"], attribute="enabled")
#         ],
#     )
#     notOneOfRule = Rule(
#         allocation_key="allocation",
#         conditions=[
#             Condition(
#                 operator=OperatorType.NOT_ONE_OF, value=["True"], attribute="enabled"
#             )
#         ],
#     )
#     assert find_matching_rule({"enabled": True}, [oneOfRule]) == oneOfRule
#     assert find_matching_rule({"enabled": False}, [oneOfRule]) is None
#     assert find_matching_rule({"enabled": True}, [notOneOfRule]) is None
#     assert find_matching_rule({"enabled": False}, [notOneOfRule]) == notOneOfRule


# def test_one_of_operator_case_insensitive():
#     oneOfRule = Rule(
#         allocation_key="allocation",
#         conditions=[
#             Condition(
#                 operator=OperatorType.ONE_OF, value=["1Ab", "Ron"], attribute="name"
#             )
#         ],
#     )
#     assert find_matching_rule({"name": "ron"}, [oneOfRule]) == oneOfRule
#     assert find_matching_rule({"name": "1AB"}, [oneOfRule]) == oneOfRule


# def test_not_one_of_operator_case_insensitive():
#     notOneOf = Rule(
#         allocation_key="allocation",
#         conditions=[
#             Condition(
#                 operator=OperatorType.NOT_ONE_OF,
#                 value=["bbB", "1.1.ab"],
#                 attribute="name",
#             )
#         ],
#     )
#     assert find_matching_rule({"name": "BBB"}, [notOneOf]) is None
#     assert find_matching_rule({"name": "1.1.AB"}, [notOneOf]) is None


# def test_one_of_operator_with_string():
#     oneOfRule = Rule(
#         allocation_key="allocation",
#         conditions=[
#             Condition(
#                 operator=OperatorType.ONE_OF, value=["john", "ron"], attribute="name"
#             )
#         ],
#     )
#     notOneOfRule = Rule(
#         allocation_key="allocation",
#         conditions=[
#             Condition(operator=OperatorType.NOT_ONE_OF, value=["ron"], attribute="name")
#         ],
#     )
#     assert find_matching_rule({"name": "john"}, [oneOfRule]) == oneOfRule
#     assert find_matching_rule({"name": "ron"}, [oneOfRule]) == oneOfRule
#     assert find_matching_rule({"name": "sam"}, [oneOfRule]) is None
#     assert find_matching_rule({"name": "ron"}, [notOneOfRule]) is None
#     assert find_matching_rule({"name": "sam"}, [notOneOfRule]) == notOneOfRule


# def test_one_of_operator_with_number():
#     oneOfRule = Rule(
#         allocation_key="allocation",
#         conditions=[
#             Condition(
#                 operator=OperatorType.ONE_OF, value=["14", "15.11"], attribute="number"
#             )
#         ],
#     )
#     notOneOfRule = Rule(
#         allocation_key="allocation",
#         conditions=[
#             Condition(
#                 operator=OperatorType.NOT_ONE_OF, value=["10"], attribute="number"
#             )
#         ],
#     )
#     assert find_matching_rule({"number": "14"}, [oneOfRule]) == oneOfRule
#     assert find_matching_rule({"number": 15.11}, [oneOfRule]) == oneOfRule
#     assert find_matching_rule({"number": "10"}, [oneOfRule]) is None
#     assert find_matching_rule({"number": "10"}, [notOneOfRule]) is None
#     assert find_matching_rule({"number": 11}, [notOneOfRule]) == notOneOfRule
