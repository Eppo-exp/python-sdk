from typing import Any
from pydantic.dataclasses import dataclass
from requests.adapters import HTTPAdapter, Retry
from http import HTTPStatus

import requests

from eppo_client.base_model import SdkBaseModel


class SdkParams(SdkBaseModel):
    # attributes are camelCase because that's what the backend endpoint expects
    apiKey: str
    sdkName: str
    sdkVersion: str


class HttpRequestError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code

    def is_recoverable(self) -> bool:
        if self.status_code >= 400 and self.status_code < 500:
            return (
                self.status_code == HTTPStatus.TOO_MANY_REQUESTS
                or self.status_code == HTTPStatus.REQUEST_TIMEOUT
            )
        return True


REQUEST_TIMEOUT_SECONDS = 2
# Retry reference: https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html#module-urllib3.util.retry
# This applies only to failed DNS lookups and connection timeouts, never to requests where data has made it to the server.
MAX_RETRIES = Retry(total=3, backoff_factor=1)


class HttpClient:
    def __init__(self, base_url: str, sdk_params: SdkParams):
        self.__base_url = base_url
        self.__sdk_params = sdk_params
        self.__session = requests.Session()
        self.__session.mount("https://", HTTPAdapter(max_retries=MAX_RETRIES))
        self.__is_unauthorized = False

    def is_unauthorized(self) -> bool:
        return self.__is_unauthorized

    def get(self, resource: str) -> Any:
        response = self.__session.get(
            self.__base_url + resource,
            params=self.__sdk_params.dict(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        self.__is_unauthorized = response.status_code == HTTPStatus.UNAUTHORIZED
        if response.status_code == HTTPStatus.OK.value:
            return response.json()
        raise HttpRequestError(
            "HTTP {} error while requesting resource {}".format(
                response.status_code, resource
            ),
            status_code=response.status_code,
        )
