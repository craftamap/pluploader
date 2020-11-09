import typing

import requests
from furl import furl

from .upmapi import PluginDto

UPM_API_ENDPOINT: str = "/rest/plugins/1.0/"


def install_plugin(base_url: furl, plugin_uri: furl, token: str) -> furl:
    request_url = base_url.copy()
    request_url.set(args={"token": token})
    request_url.add(path=UPM_API_ENDPOINT)
    response = requests.post(
        request_url.url,
        json={"pluginUri": plugin_uri.url},
        headers={"Content-Type": "application/vnd.atl.plugins.remote.install+json"},
    )
    if response.status_code != 200:
        pass
        # TODO: Throw Exception or smth
    return response.json().get("links", {}).get("self")


def install_plugin_get_current_progress(base_url: furl, progress_path: furl) -> (int, typing.Optional[PluginDto]):
    request_url: furl = base_url.copy()
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
    # TODO: find better check then "type"
    if "type" in response_json:
        progress = int(response_json.get("status", {}).get("amountDownloaded", 0))
        return progress, None
    return 0, None
