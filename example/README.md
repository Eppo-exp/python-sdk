# Running the Eppo SDK examples
Before running the example, you need to install the dependencies for the Eppo SDK.

From the root of the repo, install the necessary requirements:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Note that all these examples query feature flags set up within the Eppo UI. 
Make sure to set up flags prior to running the examples and adjusting the scripts accordingly.


## 01: Local script

This is the simplest example that shows how to use the Eppo SDK.  Set your API key in `01_script.py`:
```
API_KEY = "[replace with your API key]"
```

Then run the example:
```
python 01_script.py
```

## 02: FastAPI

Generally, Eppo is configured as part of a server. This example shows how to use the Eppo SDK in a FastAPI server.
To follow best practices, create a .env file by copying .env.dist and put your API key in it. 
We will use `python-dotenv` to read the SDK key from the .env file.

Then run the example:
```
fastapi dev 02_fastapi.py
```

## 03: Bandit

This example builds on the previous FastAPI example but instead of showing a simple feature flag, it shows how to use Eppo's contextual bandits.

Make sure you have your Eppo API key set in `.env` as instructed above, then run the example:
```
fastapi dev 03_bandit.py
```