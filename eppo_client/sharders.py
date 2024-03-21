from abc import ABC, abstractmethod
from typing import Dict
import hashlib


class Sharder(ABC):
    @abstractmethod
    def get_shard(self, input: str, total_shards: int) -> int: ...


class MD5Sharder(Sharder):
    def get_shard(self, input: str, total_shards: int) -> int:
        hash_output = hashlib.md5(input.encode("utf-8")).hexdigest()
        # get the first 4 bytes of the md5 hex string and parse it using base 16
        # (8 hex characters represent 4 bytes, e.g. 0xffffffff represents the max 4-byte integer)
        int_from_hash = int(hash_output[0:8], 16)
        return int_from_hash % total_shards


class DeterministicSharder(Sharder):
    """
    Deterministic sharding based on a look-up table
    to simplify writing tests
    """

    def __init__(self, lookup: Dict[str, int]):
        self.lookup = lookup

    def get_shard(self, input: str, total_shards: int) -> int:
        return self.lookup.get(input, 0)
