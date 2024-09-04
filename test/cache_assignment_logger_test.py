from unittest.mock import Mock

from cachetools import LRUCache

from eppo_client.assignment_logger import AssignmentCacheLogger
from eppo_client.client import _utcnow
from eppo_client.version import __version__


def test_non_caching():
    inner = Mock()
    logger = AssignmentCacheLogger(inner)

    logger.log_assignment(make_assignment_event())
    logger.log_assignment(make_assignment_event())
    logger.log_bandit_action(make_bandit_event())
    logger.log_bandit_action(make_bandit_event())

    assert inner.log_assignment.call_count == 2
    assert inner.log_bandit_action.call_count == 2


def test_assignment_cache():
    inner = Mock()
    logger = AssignmentCacheLogger(inner, assignment_cache=LRUCache(100))

    logger.log_assignment(make_assignment_event())
    logger.log_assignment(make_assignment_event())

    assert inner.log_assignment.call_count == 1


def test_bandit_cache():
    inner = Mock()
    logger = AssignmentCacheLogger(inner, bandit_cache=LRUCache(100))

    logger.log_bandit_action(make_bandit_event())
    logger.log_bandit_action(make_bandit_event())

    assert inner.log_bandit_action.call_count == 1


def test_bandit_flip_flop():
    inner = Mock()
    logger = AssignmentCacheLogger(inner, bandit_cache=LRUCache(100))

    logger.log_bandit_action(make_bandit_event(action="action1"))
    logger.log_bandit_action(make_bandit_event(action="action1"))
    assert inner.log_bandit_action.call_count == 1

    logger.log_bandit_action(make_bandit_event(action="action2"))
    assert inner.log_bandit_action.call_count == 2

    logger.log_bandit_action(make_bandit_event(action="action1"))
    assert inner.log_bandit_action.call_count == 3


def make_assignment_event(
    *,
    allocation="allocation",
    experiment="experiment",
    featureFlag="featureFlag",
    variation="variation",
    subject="subject",
    timestamp=_utcnow().isoformat(),
    subjectAttributes={},
    metaData={"sdkLanguage": "python", "sdkVersion": __version__},
    extra_logging={},
):
    return {
        **extra_logging,
        "allocation": allocation,
        "experiment": experiment,
        "featureFlag": featureFlag,
        "variation": variation,
        "subject": subject,
        "timestamp": timestamp,
        "subjectAttributes": subjectAttributes,
        "metaData": metaData,
    }


def make_bandit_event(
    *,
    flag_key="flagKey",
    bandit_key="banditKey",
    subject_key="subjectKey",
    action="action",
    action_probability=1.0,
    optimality_gap=None,
    evaluation=None,
    bandit_data=None,
    subject_context_attributes=None,
    timestamp=_utcnow().isoformat(),
    model_version="model_version",
    meta_data={"sdkLanguage": "python", "sdkVersion": __version__},
):
    return {
        "flagKey": flag_key,
        "banditKey": bandit_key,
        "subject": subject_key,
        "action": action,
        "actionProbability": action_probability,
        "optimalityGap": optimality_gap,
        "modelVersion": model_version,
        "timestamp": timestamp,
        "subjectNumericAttributes": {},
        "subjectCategoricalAttributes": {},
        "actionNumericAttributes": {},
        "actionCategoricalAttributes": {},
        "metaData": meta_data,
    }
