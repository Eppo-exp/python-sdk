from eppo_client.rules import OperatorType, Rule, Condition, matches_any_rule

greater_than_condition = Condition(operator=OperatorType.GT, value=10, attribute="age")
less_than_condition = Condition(operator=OperatorType.LT, value=100, attribute="age")
numeric_rule = Rule(conditions=[less_than_condition, greater_than_condition])

matches_email_condition = Condition(
    operator=OperatorType.MATCHES, value=".*@email.com", attribute="email"
)
text_rule = Rule(conditions=[matches_email_condition])

rule_with_empty_conditions = Rule(conditions=[])


def test_matches_rules_false_with_empty_rules():
    subject_attributes = {"age": 20, "country": "US"}
    assert matches_any_rule(subject_attributes, []) is False


def test_matches_rules_false_when_no_rules_match():
    subject_attributes = {"age": 99, "country": "US", "email": "test@example.com"}
    assert matches_any_rule(subject_attributes, [text_rule]) is False


def test_matches_rules_true_on_match():
    assert matches_any_rule({"age": 99}, [numeric_rule]) is True
    assert matches_any_rule({"email": "testing@email.com"}, [text_rule]) is True


def test_matches_rules_false_if_no_attribute_for_condition():
    assert matches_any_rule({}, [numeric_rule]) is False


def test_matches_rules_true_if_no_conditions_for_rule():
    assert matches_any_rule({}, [rule_with_empty_conditions]) is True


def test_matches_rules_false_if_numeric_operator_with_string():
    assert matches_any_rule({"age": "99"}, [numeric_rule]) is False


def test_matches_rules_true_with_numeric_value_and_regex():
    condition = Condition(
        operator=OperatorType.MATCHES, value="[0-9]+", attribute="age"
    )
    rule = Rule(conditions=[condition])
    assert matches_any_rule({"age": 99}, [rule]) is True


def test_one_of_operator_with_boolean():
    oneOfRule = Rule(
        conditions=[
            Condition(operator=OperatorType.ONE_OF, value=["True"], attribute="enabled")
        ]
    )
    notOneOfRule = Rule(
        conditions=[
            Condition(
                operator=OperatorType.NOT_ONE_OF, value=["True"], attribute="enabled"
            )
        ]
    )
    assert matches_any_rule({"enabled": True}, [oneOfRule]) is True
    assert matches_any_rule({"enabled": False}, [oneOfRule]) is False
    assert matches_any_rule({"enabled": True}, [notOneOfRule]) is False
    assert matches_any_rule({"enabled": False}, [notOneOfRule]) is True


def test_one_of_operator_case_insensitive():
    oneOfRule = Rule(
        conditions=[
            Condition(
                operator=OperatorType.ONE_OF, value=["1Ab", "Ron"], attribute="name"
            )
        ]
    )
    assert matches_any_rule({"name": "ron"}, [oneOfRule]) is True
    assert matches_any_rule({"name": "1AB"}, [oneOfRule]) is True


def test_not_one_of_operator_case_insensitive():
    notOneOf = Rule(
        conditions=[
            Condition(
                operator=OperatorType.NOT_ONE_OF,
                value=["bbB", "1.1.ab"],
                attribute="name",
            )
        ]
    )
    assert matches_any_rule({"name": "BBB"}, [notOneOf]) is False
    assert matches_any_rule({"name": "1.1.AB"}, [notOneOf]) is False


def test_one_of_operator_with_string():
    oneOfRule = Rule(
        conditions=[
            Condition(
                operator=OperatorType.ONE_OF, value=["john", "ron"], attribute="name"
            )
        ]
    )
    notOneOfRule = Rule(
        conditions=[
            Condition(operator=OperatorType.NOT_ONE_OF, value=["ron"], attribute="name")
        ]
    )
    assert matches_any_rule({"name": "john"}, [oneOfRule]) is True
    assert matches_any_rule({"name": "ron"}, [oneOfRule]) is True
    assert matches_any_rule({"name": "sam"}, [oneOfRule]) is False
    assert matches_any_rule({"name": "ron"}, [notOneOfRule]) is False
    assert matches_any_rule({"name": "sam"}, [notOneOfRule]) is True


def test_one_of_operator_with_number():
    oneOfRule = Rule(
        conditions=[
            Condition(
                operator=OperatorType.ONE_OF, value=["14", "15.11"], attribute="number"
            )
        ]
    )
    notOneOfRule = Rule(
        conditions=[
            Condition(
                operator=OperatorType.NOT_ONE_OF, value=["10"], attribute="number"
            )
        ]
    )
    assert matches_any_rule({"number": "14"}, [oneOfRule]) is True
    assert matches_any_rule({"number": 15.11}, [oneOfRule]) is True
    assert matches_any_rule({"number": "10"}, [oneOfRule]) is False
    assert matches_any_rule({"number": "10"}, [notOneOfRule]) is False
    assert matches_any_rule({"number": 11}, [notOneOfRule]) is True
