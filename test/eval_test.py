import datetime

from eppo_client.models import Flag, Allocation, Range, Variation, Split, Shard
from eppo_client.eval import Evaluator, FlagEvaluation, is_in_shard_range, seed
from eppo_client.rules import Condition, OperatorType, Rule
from eppo_client.sharding import DeterministicSharder, MD5Sharder


def test_disabled_flag_returns_none_result():
    flag = Flag(
        key="disabled_flag",
        enabled=False,
        variations={"a": Variation(key="a", value="A")},
        allocations=[
            Allocation(
                key="default", rules=[], splits=[Split(variation_key="a", shards=[])]
            )
        ],
        total_shards=10,
    )

    evaluator = Evaluator(sharder=MD5Sharder())
    result = evaluator.evaluate_flag(flag, "subject_key", {})
    assert result.flag_key == "disabled_flag"
    assert result.allocation_key == None
    assert result.variation == None
    assert not result.do_log


def test_matches_shard_full_range():
    shard = Shard(
        salt="a",
        ranges=[Range(start=0, end=100)],
    )

    evaluator = Evaluator(sharder=MD5Sharder())
    assert evaluator.matches_shard(shard, "subject_key", 100) is True


def test_matches_shard_full_range_split():
    shard = Shard(
        salt="a",
        ranges=[Range(start=0, end=50), Range(start=50, end=100)],
    )

    evaluator = Evaluator(sharder=MD5Sharder())
    assert evaluator.matches_shard(shard, "subject_key", 100) is True


def test_matches_shard_no_match():
    shard = Shard(
        salt="a",
        ranges=[Range(start=0, end=50)],
    )

    evaluator = Evaluator(sharder=DeterministicSharder({"a-subject_key": 99}))
    assert evaluator.matches_shard(shard, "subject_key", 100) is False


def test_eval_empty_flag():
    empty_flag = Flag(
        key="empty",
        enabled=True,
        variations={
            "a": Variation(key="a", value="A"),
            "b": Variation(key="b", value="B"),
        },
        allocations=[],
        total_shards=10,
    )

    evaluator = Evaluator(sharder=MD5Sharder())
    assert evaluator.evaluate_flag(empty_flag, "subject_key", {}) == FlagEvaluation(
        flag_key="empty",
        subject_key="subject_key",
        subject_attributes={},
        allocation_key=None,
        variation=None,
        extra_logging={},
        do_log=False,
    )


def test_catch_all_allocation():
    flag = Flag(
        key="flag",
        enabled=True,
        variations={
            "a": Variation(key="a", value="A"),
            "b": Variation(key="b", value="B"),
        },
        allocations=[
            Allocation(
                key="default",
                rules=[],
                splits=[Split(variation_key="a", shards=[])],
            )
        ],
        total_shards=10,
    )

    evaluator = Evaluator(sharder=MD5Sharder())
    result = evaluator.evaluate_flag(flag, "subject_key", {})
    assert result.flag_key == "flag"
    assert result.allocation_key == "default"
    assert result.variation == Variation(key="a", value="A")
    assert result.do_log


def test_match_first_allocation_rule():
    flag = Flag(
        key="flag",
        enabled=True,
        variations={
            "a": Variation(key="a", value="A"),
            "b": Variation(key="b", value="B"),
        },
        allocations=[
            Allocation(
                key="first",
                rules=[
                    Rule(
                        conditions=[
                            Condition(
                                operator=OperatorType.MATCHES,
                                attribute="email",
                                value=".*@example.com",
                            )
                        ]
                    )
                ],
                splits=[Split(variation_key="b", shards=[])],
            ),
            Allocation(
                key="default",
                rules=[],
                splits=[Split(variation_key="a", shards=[])],
            ),
        ],
        total_shards=10,
    )

    evaluator = Evaluator(sharder=MD5Sharder())
    result = evaluator.evaluate_flag(flag, "subject_key", {"email": "eppo@example.com"})
    assert result.flag_key == "flag"
    assert result.allocation_key == "first"
    assert result.variation == Variation(key="b", value="B")


def test_do_not_match_first_allocation_rule():
    flag = Flag(
        key="flag",
        enabled=True,
        variations={
            "a": Variation(key="a", value="A"),
            "b": Variation(key="b", value="B"),
        },
        allocations=[
            Allocation(
                key="first",
                rules=[
                    Rule(
                        conditions=[
                            Condition(
                                operator=OperatorType.MATCHES,
                                attribute="email",
                                value=".*@example.com",
                            )
                        ]
                    )
                ],
                splits=[Split(variation_key="b", shards=[])],
            ),
            Allocation(
                key="default",
                rules=[],
                splits=[Split(variation_key="a", shards=[])],
            ),
        ],
        total_shards=10,
    )

    evaluator = Evaluator(sharder=MD5Sharder())
    result = evaluator.evaluate_flag(flag, "subject_key", {"email": "eppo@test.com"})
    assert result.flag_key == "flag"
    assert result.allocation_key == "default"
    assert result.variation == Variation(key="a", value="A")


def test_eval_sharding():
    flag = Flag(
        key="flag",
        enabled=True,
        variations={
            "a": Variation(key="a", value="A"),
            "b": Variation(key="b", value="B"),
            "c": Variation(key="c", value="C"),
        },
        allocations=[
            Allocation(
                key="first",
                rules=[],
                splits=[
                    Split(
                        variation_key="a",
                        shards=[
                            Shard(salt="traffic", ranges=[Range(start=0, end=5)]),
                            Shard(salt="split", ranges=[Range(start=0, end=3)]),
                        ],
                    ),
                    Split(
                        variation_key="b",
                        shards=[
                            Shard(salt="traffic", ranges=[Range(start=0, end=5)]),
                            Shard(salt="split", ranges=[Range(start=3, end=6)]),
                        ],
                    ),
                ],
            ),
            Allocation(
                key="default",
                rules=[],
                splits=[Split(variation_key="c", shards=[])],
            ),
        ],
        total_shards=10,
    )

    evaluator = Evaluator(
        sharder=DeterministicSharder(
            {
                "traffic-alice": 2,
                "traffic-bob": 3,
                "traffic-charlie": 4,
                "traffic-dave": 7,
                "split-alice": 1,
                "split-bob": 4,
                "split-charlie": 8,
                "split-dave": 1,
            }
        )
    )

    result = evaluator.evaluate_flag(flag, "alice", {})
    assert result.allocation_key == "first"
    assert result.variation == Variation(key="a", value="A")

    result = evaluator.evaluate_flag(flag, "bob", {})
    assert result.allocation_key == "first"
    assert result.variation == Variation(key="b", value="B")

    # charlie matches on traffic but not on split and falls through
    result = evaluator.evaluate_flag(flag, "charlie", {})
    assert result.allocation_key == "default"
    assert result.variation == Variation(key="c", value="C")

    # dave does not match traffic
    result = evaluator.evaluate_flag(flag, "dave", {})
    assert result.allocation_key == "default"
    assert result.variation == Variation(key="c", value="C")


def test_eval_prior_to_alloc(mocker):
    flag = Flag(
        key="flag",
        enabled=True,
        variations={"a": Variation(key="a", value="A")},
        allocations=[
            Allocation(
                key="default",
                start_at=datetime.datetime(2024, 1, 1),
                end_at=datetime.datetime(2024, 2, 1),
                rules=[],
                splits=[Split(variation_key="a", shards=[])],
            )
        ],
        total_shards=10,
    )

    evaluator = Evaluator(sharder=MD5Sharder())
    with mocker.patch(
        "eppo_client.eval.utcnow", return_value=datetime.datetime(2023, 1, 1)
    ):
        result = evaluator.evaluate_flag(flag, "subject_key", {})
        assert result.flag_key == "flag"
        assert result.allocation_key == None
        assert result.variation == None


def test_eval_during_alloc(mocker):
    flag = Flag(
        key="flag",
        enabled=True,
        variations={"a": Variation(key="a", value="A")},
        allocations=[
            Allocation(
                key="default",
                start_at=datetime.datetime(2024, 1, 1),
                end_at=datetime.datetime(2024, 2, 1),
                rules=[],
                splits=[Split(variation_key="a", shards=[])],
            )
        ],
        total_shards=10,
    )

    evaluator = Evaluator(sharder=MD5Sharder())
    with mocker.patch(
        "eppo_client.eval.utcnow", return_value=datetime.datetime(2024, 1, 5)
    ):
        result = evaluator.evaluate_flag(flag, "subject_key", {})
        assert result.flag_key == "flag"
        assert result.allocation_key == "default"
        assert result.variation == Variation(key="a", value="A")


def test_eval_after_alloc(mocker):
    flag = Flag(
        key="flag",
        enabled=True,
        variations={"a": Variation(key="a", value="A")},
        allocations=[
            Allocation(
                key="default",
                start_at=datetime.datetime(2024, 1, 1),
                end_at=datetime.datetime(2024, 2, 1),
                rules=[],
                splits=[Split(variation_key="a", shards=[])],
            )
        ],
        total_shards=10,
    )

    evaluator = Evaluator(sharder=MD5Sharder())
    with mocker.patch(
        "eppo_client.eval.utcnow", return_value=datetime.datetime(2024, 2, 5)
    ):
        result = evaluator.evaluate_flag(flag, "subject_key", {})
        assert result.flag_key == "flag"
        assert result.allocation_key == None
        assert result.variation == None


def test_seed():
    assert seed("salt", "subject") == "salt-subject"


def test_is_in_shard_range():
    assert is_in_shard_range(5, Range(start=0, end=10)) is True
    assert is_in_shard_range(10, Range(start=0, end=10)) is False
    assert is_in_shard_range(0, Range(start=0, end=10)) is True
    assert is_in_shard_range(0, Range(start=0, end=0)) is False
    assert is_in_shard_range(0, Range(start=0, end=1)) is True
    assert is_in_shard_range(1, Range(start=0, end=1)) is False
    assert is_in_shard_range(1, Range(start=1, end=1)) is False
