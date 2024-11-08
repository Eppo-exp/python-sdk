# Eppo Python SDK

This repository has been migrated to [https://github.com/Eppo-exp/eppo-multiplatform](https://github.com/Eppo-exp/eppo-multiplatform).

[Eppo](https://www.geteppo.com/) is a modular flagging and experimentation analysis tool. Eppo's Python SDK is built to make assignments in multi-user server side contexts. Before proceeding you'll need an Eppo account.

## Features

- Feature gates
- Kill switches
- Progressive rollouts
- A/B/n experiments
- Mutually exclusive experiments (Layers)
- Dynamic configuration

## Installation

```shell
pip install eppo-server-sdk
```

## Quick start

Begin by initializing a singleton instance of Eppo's client. Once initialized, the client can be used to make assignments anywhere in your app.

#### Initialize once

```python
import eppo_client
from eppo_client.config import Config, AssignmentLogger

client_config = Config(api_key="<SDK-KEY-FROM-DASHBOARD>")
eppo_client.init(client_config)
```


#### Assign anywhere

```python
import eppo_client

client = eppo_client.get_instance()
user = get_current_user()

variation = eppoClient.get_boolean_assignment(
    'show-new-feature', 
    user.id, 
    { 'country': user.country }, 
    False
)
```

## Assignment functions

Every Eppo flag has a return type that is set once on creation in the dashboard. Once a flag is created, assignments in code should be made using the corresponding typed function:

```python
get_boolean_assignment(...)
get_numeric_assignment(...)
get_integer_assignment(...)
get_string_assignment(...)
get_json_assignment(...)
```

Each function has the same signature, but returns the type in the function name. For booleans use `get_boolean_assignment`, which has the following signature:

```python
get_boolean_assignment(
    flag_key: str,
    subject_key: str,
    subject_attributes: Dict[str, Any],
    default_value: bool
) -> bool:
  ```

## Initialization options

The `init` function accepts the following optional configuration arguments.

| Option | Type | Description | Default |
| ------ | ----- | ----- | ----- |
| **`assignment_logger`**  | [AssignmentLogger](https://github.com/Eppo-exp/python-sdk/blob/ebc1a0b781769fe9d2e2be6fc81779eb8685a6c7/eppo_client/assignment_logger.py#L6-L10) | A callback that sends each assignment to your data warehouse. Required only for experiment analysis. See [example](#assignment-logger) below. | `None` |
| **`is_graceful_mode`** | bool | When true, gracefully handles all exceptions within the assignment function and returns the default value. | `True` |
| **`poll_interval_seconds`** | Optional[int] | The interval in seconds at which the SDK polls for configuration updates. If set to `None`, polling is disabled. | `300` |
| **`poll_jitter_seconds`** | int | The jitter in seconds to add to the poll interval. | `30` |
| **`initial_configuration`** | Optional[Configuration] | If set, the client will use this configuration until it fetches a fresh one. | `None` |

## Assignment logger

To use the Eppo SDK for experiments that require analysis, pass in a callback logging function to the `init` function on SDK initialization. The SDK invokes the callback to capture assignment data whenever a variation is assigned. The assignment data is needed in the warehouse to perform analysis.

The code below illustrates an example implementation of a logging callback using [Segment](https://segment.com/), but you can use any system you'd like. The only requirement is that the SDK receives a `log_assignment` callback function. Here we define an implementation of the Eppo `SegmentAssignmentLogger` interface containing a single function named `log_assignment`:

```python
from eppo_client.assignment_logger import AssignmentLogger
import analytics

# Connect to Segment.
analytics.write_key = "<SEGMENT_WRITE_KEY>"

class SegmentAssignmentLogger(AssignmentLogger):
    def log_assignment(self, assignment):
        analytics.track(assignment["subject"], "Eppo Randomization Assignment", assignment)

client_config = Config(api_key="<SDK-KEY-FROM-DASHBOARD>", assignment_logger=SegmentAssignmentLogger())
```

### De-duplication of assignments

The SDK may see many duplicate assignments in a short period of time, and if you have configured a logging function, they will be transmitted to your downstream event store. This increases the cost of storage as well as warehouse costs during experiment analysis.

To mitigate this, a caching assignment logger is optionally available with configurable cache behavior.

The caching can be configured individually for assignment logs and bandit action logs using `AssignmentCacheLogger`.

`AssignmentCacheLogger` optionally accepts two caches. We recommend using [`cachetools`](https://pypi.org/project/cachetools/) but any subclass of `MutableMapping` works.

```python
import cachetools
from eppo_client.assignment_logger import AssignmentLogger, AssignmentCacheLogger


class MyLogger(AssignmentLogger):
    # implement your logger
    pass


client_config = Config(
    api_key="<SDK-KEY-FROM-DASHBOARD>",
    assignment_logger=AssignmentCacheLogger(
        MyLogger(),
        # cache 1024 least recently used assignments
        assignment_cache=cachetools.LRUCache(maxsize=1024),
        # cache bandit assignment for no longer than 10 minutes
        bandit_cache=cachetools.TTLCache(maxsize=2048, ttl=600),
    ),
)
```

## Export configuration

To support the use-case of needing to bootstrap a front-end client, the Eppo SDK provides a function to export flag configurations to a JSON string.

Use the `get_flag_configurations` function to export flag configurations to a JSON string and then send it to the front-end client.

```python
from fastapi import JSONResponse

import eppo_client
import json

client = eppo_client.get_instance()
flag_configurations = client.get_flag_configurations()

# Convert flag configurations to a JSON string
flag_config_json = json.dumps(flag_configurations)

# Create a JSONResponse object with the stringified JSON
response = JSONResponse(content={"flagConfigurations": flag_config_json})
```

## Philosophy

Eppo's SDKs are built for simplicity, speed and reliability. Flag configurations are compressed and distributed over a global CDN (Fastly), typically reaching your servers in under 15ms. Server SDKs continue polling Eppo’s API at 30-second intervals. Configurations are then cached locally, ensuring that each assignment is made instantly. Evaluation logic within each SDK consists of a few lines of simple numeric and string comparisons. The typed functions listed above are all developers need to understand, abstracting away the complexity of the Eppo's underlying (and expanding) feature set.

## Contributing

To publish a new version of the SDK, set the version as desired in `eppo_client/version.py`, then create a new Github release. The CI/CD configuration will handle the build and publish to PyPi.
