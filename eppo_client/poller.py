import logging
from multiprocessing import Event
from random import randrange
from threading import Thread
from typing import Callable

logger = logging.getLogger(__name__)


class Poller:
    def __init__(self, interval_millis: int, jitter_millis: int, callback: Callable):
        self.__jitter_millis = jitter_millis
        self.__interval = interval_millis
        self.__stop_event = Event()
        self.__callback = callback
        self.__thread = Thread(target=self.poll, daemon=True)

    def start(self):
        self.__thread.start()

    def stop(self):
        self.__stop_event.set()

    def is_stopped(self):
        return self.__stop_event.is_set()

    def poll(self):
        while not self.is_stopped():
            try:
                self.__callback()
            except Exception as e:
                logger.error("Unexpected error running poll task: " + str(e))
                break
            self._wait_for_interval()

    def _wait_for_interval(self):
        interval_with_jitter = self.__interval - randrange(0, self.__jitter_millis)
        self.__stop_event.wait(interval_with_jitter / 1000)
