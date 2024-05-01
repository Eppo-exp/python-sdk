from typing import Dict, Optional, TypeVar, Generic

from eppo_client.read_write_lock import ReadWriteLock

T = TypeVar("T")


class ConfigurationStore(Generic[T]):
    def __init__(self):
        self.__cache: Dict[str, T] = {}
        self.__lock = ReadWriteLock()

    def get_configuration(self, key: str) -> Optional[T]:
        with self.__lock.reader():
            return self.__cache.get(key, None)

    def set_configurations(self, configs: Dict[str, T]):
        with self.__lock.writer():
            self.__cache.clear()
            for key, config in configs.items():
                self.__cache[key] = config

    def get_keys(self):
        with self.__lock.reader():
            return list(self.__cache.keys())
