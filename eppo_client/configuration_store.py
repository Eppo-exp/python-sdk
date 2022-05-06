from typing import Dict, Optional, TypeVar, Generic
from cachetools import LRUCache

from eppo_client.read_write_lock import ReadWriteLock

T = TypeVar("T")


class ConfigurationStore(Generic[T]):
    def __init__(self, max_size: int):
        self.__cache: LRUCache = LRUCache(maxsize=max_size)
        self.__lock = ReadWriteLock()

    def get_configuration(self, key: str) -> Optional[T]:
        try:
            self.__lock.acquire_read()
            return self.__cache[key]
        except KeyError:
            return None  # key does not exist
        finally:
            self.__lock.release_read()

    def set_configurations(self, configs: Dict[str, T]):
        try:
            self.__lock.acquire_write()
            for key, config in configs.items():
                self.__cache[key] = config
        finally:
            self.__lock.release_write()
