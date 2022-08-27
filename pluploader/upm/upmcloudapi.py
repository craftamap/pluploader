import dataclasses
import typing
from enum import Enum

import requests
from furl import furl

from .exceptions import UploadFailedException
from .upmapi import PluginDto, UpmApi


@dataclasses.dataclass(frozen=True)
class Token:
    pluginKey: str
    token: str
    state: str
    valid: bool

    @classmethod
    def decode(cls, obj: dict) -> "Token":
        return cls(pluginKey=obj.get("pluginKey"), token=obj.get("token"), state=obj.get("state"), valid=obj.get("valid"),)

    class TokenState(Enum):
        NONE = "NONE"
        ACTIVE_TRIAL = "ACTIVE_TRIAL"
        INACTIVE_TRIAL = "INACTIVE_TRIAL"
        ACTIVE_SUBSCRIPTION = "ACTIVE_SUBSCRIPTION"
        ACTIVE_SUBSCRIPTION_CANCELLED = "ACTIVE_SUBSCRIPTION_CANCELLED"
        INACTIVE_SUBSCRIPTION = "INACTIVE_SUBSCRIPTION"


class UpmCloudApi(UpmApi):
    def install_plugin(self, plugin_uri: furl, token: str) -> furl:
        request_url = self.base_url.copy()
        request_url.set(args={"token": token})
        request_url.add(path=self.UPM_API_ENDPOINT)
        response = requests.post(
            request_url.url,
            json={"pluginUri": plugin_uri.url},
            headers={"Content-Type": "application/vnd.atl.plugins.remote.install+json"},
        )
        if response.status_code < 200 or response.status_code > 299:
            raise UploadFailedException("Upload was unsuccessful", response.status_code)
        return response.json().get("links", {}).get("self", None)

    def install_plugin_get_current_progress(self, progress_path: furl) -> (int, typing.Optional[PluginDto]):
        request_url: furl = self.base_url.copy()
        request_url.set(path=progress_path)
        response = requests.get(
            request_url.url,
            headers={"Content-Type": "application/vnd.atl.plugins.install.downloading+json"},
            allow_redirects=True,
        )
        if len(response.history) > 0:
            # If we got redirected, we assume that we got redirected to the plugins page
            return 100, PluginDto.decode(response.json())
        response_json = response.json()
        status = response_json.get("status", {})
        if status.get("done", False) and status.get("subCode"):
            raise UploadFailedException(
                "Upload was unsuccessful",
                status.get("subCode"),
                status.get("contentType"),
                status.get("exception") or status.get("errorMessage"),
            )
        # TODO: find better check then "type"
        if "type" in response_json:
            progress = int(response_json.get("status", {}).get("amountDownloaded", 0))
            return progress, None
        return 0, None

    def list_access_token(self) -> typing.List[Token]:
        request_url = self.base_url.copy()
        request_url.add(path=self.UPM_API_ENDPOINT)
        request_url.add(path="license-tokens")
        try:
            response = requests.get(request_url.url)
            return [Token.decode(obj) for obj in response.json().get("tokens")]
        except Exception:
            raise ValueError(response.status_code, response.content)

    def get_access_token(self, plugin_key: str) -> Token:
        request_url = self.base_url.copy()
        request_url.add(path=self.UPM_API_ENDPOINT)
        request_url.add(path="license-tokens")
        request_url.add(path=f"{plugin_key}-key")
        try:
            response = requests.get(request_url.url)
            return Token.decode(response.json())
        except Exception:
            raise ValueError(response.status_code, response.content)

    def update_access_token(
        self, plugin_key: str, token: str, state: Token.TokenState = Token.TokenState.ACTIVE_SUBSCRIPTION
    ) -> Token:
        request_url = self.base_url.copy()
        request_url.add(path=self.UPM_API_ENDPOINT)
        request_url.add(path="license-tokens")
        body = {
            "pluginKey": plugin_key,
            "token": token,
            "state": state.value,
        }
        headers = {
            "Content-Type": "application/vnd.atl.plugins+json",
        }
        try:
            response = requests.post(request_url.url, json=body, headers=headers)
            if response.status_code > 299:
                raise (Exception())
            return Token.decode(response.json())

        except Exception:
            raise ValueError(response.status_code, response.content)

    def delete_access_token(
        self, plugin_key: str,
    ):
        request_url = self.base_url.copy()
        request_url.add(path=self.UPM_API_ENDPOINT)
        request_url.add(path="license-tokens")
        request_url.add(path=f"{plugin_key}-key")
        try:
            response = requests.delete(request_url.url)
            if response.status_code > 299:
                raise (Exception())
        except Exception:
            raise ValueError(response.status_code, response.content)
