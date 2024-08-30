from typing import Dict, Optional, Tuple, MutableMapping


class AssignmentLogger:
    def log_assignment(self, assignment_event: Dict):
        pass

    def log_bandit_action(self, bandit_event: Dict):
        pass


class AssignmentCacheLogger(AssignmentLogger):
    def __init__(
        self,
        inner: AssignmentLogger,
        *,
        assignment_cache: Optional[MutableMapping] = None,
        bandit_cache: Optional[MutableMapping] = None,
    ):
        self.__inner = inner
        self.__assignment_cache = assignment_cache
        self.__bandit_cache = bandit_cache

    def log_assignment(self, event: Dict):
        _cache_or_call(
            self.__assignment_cache,
            *AssignmentCacheLogger.__assignment_cache_keyvalue(event),
            lambda: self.__inner.log_assignment(event),
        )

    def log_bandit_action(self, event: Dict):
        _cache_or_call(
            self.__bandit_cache,
            *AssignmentCacheLogger.__bandit_cache_keyvalue(event),
            lambda: self.__inner.log_bandit_action(event),
        )

    @staticmethod
    def __assignment_cache_keyvalue(event: Dict) -> Tuple[Tuple, Tuple]:
        key = (event["featureFlag"], event["subject"])
        value = (event["allocation"], event["variation"])
        return key, value

    @staticmethod
    def __bandit_cache_keyvalue(event: Dict) -> Tuple[Tuple, Tuple]:
        key = (event["flagKey"], event["subject"])
        value = (event["banditKey"], event["action"])
        return key, value


def _cache_or_call(cache: Optional[MutableMapping], key, value, fn):
    if cache is not None and (previous := cache.get(key)) and previous == value:
        # ok, cached
        return

    fn()

    if cache is not None:
        cache[key] = value
