import hashlib

from eppo_client.base_model import SdkBaseModel


def get_shard(input: str, subject_shards: int):
    hash_output = hashlib.md5(input.encode("utf-8")).hexdigest()
    # get the first 4 bytes of the md5 hex string and parse it using base 16
    # (8 hex characters represent 4 bytes, e.g. 0xffffffff represents the max 4-byte integer)
    int_from_hash = int(hash_output[0:8], 16)
    return int_from_hash % subject_shards


class ShardRange(SdkBaseModel):
    start: int
    end: int


def is_in_shard_range(shard: int, range: ShardRange) -> bool:
    return shard >= range.start and shard < range.end
