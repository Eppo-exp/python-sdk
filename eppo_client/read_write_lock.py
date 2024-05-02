import threading
from contextlib import contextmanager

# Adapted from: https://www.oreilly.com/library/view/python-cookbook/0596001673/ch06s04.html


class ReadWriteLock:
    """A lock object that allows many simultaneous "read locks", but
    only one "write lock." """

    def __init__(self):
        self._read_ready = threading.Condition(threading.Lock())
        self._readers = 0

    def acquire_read(self):
        """Acquire a read lock. Blocks only if a thread has
        acquired the write lock."""
        with self._read_ready:
            self._readers += 1

    def release_read(self):
        """Release a read lock."""
        with self._read_ready:
            self._readers -= 1
            if not self._readers:
                self._read_ready.notify_all()

    def acquire_write(self):
        """Acquire a write lock. Blocks until there are no
        acquired read or write locks."""
        self._read_ready.acquire()
        while self._readers > 0:
            self._read_ready.wait()

    def release_write(self):
        """Release a write lock."""
        self._read_ready.release()

    @contextmanager
    def reader(self):
        try:
            self.acquire_read()
            yield
        finally:
            self.release_read()

    @contextmanager
    def writer(self):
        try:
            self.acquire_write()
            yield
        finally:
            self.release_write()
