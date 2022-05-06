from time import sleep
from unittest.mock import Mock
from eppo_client.poller import Poller


def test_invokes_callback_until_stopped():
    callback = Mock(return_value=None)
    task = Poller(interval_millis=10, jitter_millis=1, callback=callback)
    task.start()
    sleep(0.099)
    task.stop()
    assert callback.call_count == 10


def test_stops_polling_if_unexpected_error():
    callback = Mock(side_effect=Exception("bad request"))
    task = Poller(interval_millis=10, jitter_millis=1, callback=callback)
    task.start()
    sleep(0.099)
    task.stop()
    assert callback.call_count == 1
