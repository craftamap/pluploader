import typing

import requests
from furl import furl

from .exceptions import UploadFailedException
from .upmapi import PluginDto, UpmApi


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
        if response_json.get("status", {}).get("done", False) and "exception" in response_json.get("status", {}).get(
            "subCode", ""
        ):
            raise UploadFailedException("Upload was unsuccessful", response_json.get("status", {}).get("subCode"))
        # TODO: find better check then "type"
        if "type" in response_json:
            progress = int(response_json.get("status", {}).get("amountDownloaded", 0))
            return progress, None
        return 0, None
