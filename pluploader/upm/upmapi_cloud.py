from furl import furl
import requests
import typing

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


def install_plugin_get_current_progress(base_url: furl, progress_path: furl) -> (int, typing.Optional[str]):
    request_url: furl = base_url.copy()
    request_url.set(path=progress_path)
    response = requests.get(
        request_url.url,
        headers={"Content-Type": "application/vnd.atl.plugins.install.downloading+json"},
        allow_redirects=False,
    )
    if response.status_code == 303:
        return 100, response.headers["Location"]
    response_json = response.json()
    if "type" in response_json:
        progress = int(response_json.get("status", {}).get("amountDownloaded", 0))
        return progress, None
    return 0, None
