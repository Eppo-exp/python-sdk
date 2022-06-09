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
