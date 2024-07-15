# poller
# We accidently shipped Python with a 5 minute poll interval.
# Customers can set the poll interval to 30 seconds to match the behavior of the other server SDKs.
# Please change this to 30 seconds when ready to bump to 4.0.
POLL_JITTER_SECONDS_DEFAULT = 30  # 30 seconds
POLL_INTERVAL_SECONDS_DEFAULT = 5 * 60  # 5 minutes
