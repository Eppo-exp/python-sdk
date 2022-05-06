# configuration cache
MAX_CACHE_ENTRIES = 1000  # arbitrary; the caching library requires a max limit

# poller
SECOND_MILLIS = 1000
MINUTE_MILLIS = 60 * SECOND_MILLIS
POLL_JITTER_MILLIS = 30 * SECOND_MILLIS
POLL_INTERVAL_MILLIS = 5 * MINUTE_MILLIS
