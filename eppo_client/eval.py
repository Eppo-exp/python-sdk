from typing import Dict, Optional
from eppo_client.sharding import Sharder
from eppo_client.models import Range, Shard, Variation
from eppo_client.rules import matches_rule
from dataclasses import dataclass
import datetime


@dataclass
class FlagEvaluation:
    flag_key: str
    allocation_key: str
    variation: Variation
    extra_logging: Dict[str, str]
    do_log: bool


@dataclass
class Evaluator:
    sharder: Sharder

    def evaluate_flag(
        self, flag, subject_key, subject_attributes
    ) -> Optional[FlagEvaluation]:
        if not flag.enabled:
            return none_result(flag.key)

        now = utcnow()
        for allocation in flag.allocations:
            if allocation.start_at and now < allocation.start_at:
                continue
            if allocation.end_at and now > allocation.end_at:
                continue

            if not allocation.rules or any(
                matches_rule(rule, subject_attributes) for rule in allocation.rules
            ):
                for split in allocation.splits:
                    if all(
                        self.matches_shard(shard, subject_key, flag.total_shards)
                        for shard in split.shards
                    ):
                        return FlagEvaluation(
                            flag_key=flag.key,
                            allocation_key=allocation.key,
                            variation=flag.variations.get(split.variation_key),
                            extra_logging=split.extra_logging,
                            do_log=allocation.do_log,
                        )

        return none_result(flag.key)

    def matches_shard(self, shard: Shard, subject_key: str, total_shards: int) -> bool:
        h = self.sharder.get_shard(seed(shard.salt, subject_key), total_shards)
        return any(is_in_shard_range(h, r) for r in shard.ranges)


def is_in_shard_range(shard: int, range: Range) -> bool:
    return range.start <= shard < range.end


def seed(salt, subject_key):
    return f"{salt}-{subject_key}"


def none_result(flag_key):
    return FlagEvaluation(
        flag_key=flag_key,
        allocation_key=None,
        variation=None,
        extra_logging={},
        do_log=False,
    )


def utcnow():
    return datetime.datetime.utcnow()
