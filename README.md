# Eppo SDK for Python

## Getting Started

### Install and initialize the SDK client
Install the package:
```
python3 -m pip install --upgrade eppo-server-sdk
```

Initialize the SDK with your Eppo API key:
```
import eppo_client
from eppo_client import Config

eppo_client.init(Config(api_key="<YOUR-API-KEY>"))
```
**The `init` method should be called once on applications startup**. The initialization method kicks off a polling process to retrieve experiment configurations from Eppo at regular intervals.

### Use the client to assign variations
Prerequisite: you must have configured an experiment in Eppo. To assign variations, your experiment should have a `RUNNING` status and a non-zero traffic allocation.

Use the assignment API in any part of your code that needs to assign subjects to experiment variations:
```
import eppo_client

client = eppo_client.get_instance()
assigned_variation = client.assign("<subject>", "<experimentKey>")
```

The `subject` argument can be any entity identifier (e.g. a user ID). The experimentKey argument is the identifier of your Eppo experiment.

The `assign` function will return null if the experiment is not running or if the subject is not part of the experiment traffic allocation.

The `eppo_client.get_instance()` method returns a singleton client instance that is intended to be reused for the lifetime of your application.

## Supported Python Versions
This version of the SDK is compatible with Python 3.6 and above.
