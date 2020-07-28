""" This module provides a basic interface for the upm rest api
"""

import dataclasses
import inspect
import json
import typing

import requests
from colorama import Fore
from furl import furl
from packaging import version

UPM_API_ENDPOINT: str = "/rest/plugins/1.0/"


@dataclasses.dataclass()
class ModuleDto:
    completeKey: str
    key: typing.Optional[str]
    name: str
    enabled: bool
    optional: bool
    recognisableType: bool
    broken: bool

    @staticmethod
    def decode(obj: dict) -> typing.Union['ModuleDto', dict]:
        if "key" in obj:
            return ModuleDto(
                key=obj.get("key"),
                completeKey=obj.get("completeKey", ""),
                name=obj.get("name", ""),
                enabled=obj.get("enabled", False),
                optional=obj.get("optional", False),
                recognisableType=obj.get("recognisableType", False),
                broken=obj.get("broken", True)
            )
        return obj


@dataclasses.dataclass
class PluginDto:
    """ This class represents a plugin given by the UPM/Plugin API
    """
    key: str
    name: str
    version: version.Version
    enabled: bool
    userInstalled: bool
    description: str
    modules: typing.Optional[typing.List[ModuleDto]]

    def print_table(self, print_modules: bool):
        """Prints table view of plugin information
        """
        for key, value in self.__dict__.items():
            if key == "modules":
                if print_modules:
                    print(f"{(key + ':'):20}")
                    for module in value:
                        status = f"{Fore.GREEN}✓{Fore.RESET}" if module.enabled else f"{Fore.YELLOW}!{Fore.RESET}"
                        print(f"  {status} {module.name[:20]:20} {module.key}")
                else:
                    pass
            else:
                print(f"{(key + ':'):15} {value}")

    @staticmethod
    def decode(obj: dict) -> typing.Union['PluginDto', dict]:
        if "key" in obj:
            return PluginDto(
                key=obj.get("key"),
                name=obj.get("name", ""),
                version=obj.get("version", "0.0.1"),
                userInstalled=obj.get("userInstalled", False),
                enabled=obj.get("enabled", False),
                description=obj.get("description", ""),
                modules=[
                    ModuleDto.decode(x) for x in obj.get("modules", [])
                ]
            )
        return obj


def get_token(base_url: furl) -> str:
    """ Get token from api endpoint
    """
    token_url: furl = base_url.copy()
    token_url.add(path=UPM_API_ENDPOINT)
    token_url.set(args={"os_authType": "basic"})
    token_response = requests.head(token_url.url)
    token = token_response.headers['upm-token']
    return token


def upload_plugin(base_url: furl, files: typing.Dict, token: str) -> typing.Tuple[int, typing.Any]:
    """ Upload plugin
    """
    upload_url = base_url.copy()
    upload_url.set(args={"token": token})
    upload_url.add(path=UPM_API_ENDPOINT)
    upload_response = requests.post(upload_url.url,
                                    files=files)
    text = upload_response.text.replace("<textarea>", "").replace("</textarea>", "")
    upload_response_data = json.loads(text)
    progress = int(upload_response_data.get("status", {}).get("amountDownloaded", 0))
    return progress, upload_response_data


def get_current_progress(base_url: furl, previous_request) -> (int, typing.Dict):
    progress_url = base_url.copy()
    progress_url.set(path=previous_request["links"]["self"])
    progress_rd = requests.get(progress_url.url).json()
    if "type" in progress_rd:
        progress = int(
            progress_rd.get("status", {}).get("amountDownloaded", 0))
        return progress, progress_rd
    return 100, progress_rd


def get_all_plugins(base_url: furl, user_installed: bool = True) -> typing.List['PluginDto']:
    """ Gets a list of all installed plugins from the api and returns it
    If user_installed is set true (default), only user installed plugins are listed
    """
    request_url = base_url.copy()
    request_url.add(path=UPM_API_ENDPOINT)
    response = requests.get(request_url.url)
    return_obj = [PluginDto.decode(x) for x in response.json().get("plugins", [])]
    if user_installed:
        return_obj = filter(lambda x: x.userInstalled, return_obj)
    return return_obj


def get_plugin(base_url: furl, plugin_key: str) -> 'PluginDto':
    """ Gets Plugin info by using the UPM_API_ENDPOINT/plugin-key/ endpoint and
    returns it as a PluginDto
    """
    request_url = base_url.copy()
    request_url.add(path=UPM_API_ENDPOINT)
    request_url.join(plugin_key + "-key")
    response = requests.get(request_url.url)
    return_obj = PluginDto.decode(response.json())
    return return_obj


def enable_disable_plugin(base_url: furl, plugin_key: str, enabled: bool) -> 'PluginDto':
    """ Enables/Disables Plugin"""
    mod = {"enabled": enabled}
    return _modify_plugin(base_url, plugin_key, mod)


def _modify_plugin(base_url: furl, plugin_key: str, modifications: dict) -> 'PluginDto':
    """ Puts Changes to plugin by using the UPM_API_ENDPOINT/plugin-key/ endpoint and
    returns new infos as a PluginDto
    """
    request_url = base_url.copy()
    request_url.add(path=UPM_API_ENDPOINT)
    request_url.join(plugin_key + "-key")
    headers = {"Content-Type": "application/vnd.atl.plugins.plugin+json"}
    response = requests.put(request_url.url,
                            json=modifications,
                            headers=headers)
    return_obj = PluginDto.decode(response.json())
    return return_obj


def uninstall_plugin(base_url: furl, plugin_key: str) -> bool:
    """ Uninstalls a plugin by using the UPM_API_ENDPOINT/plugin-key/ endpoint
    """
    request_url = base_url.copy()
    request_url.add(path=UPM_API_ENDPOINT)
    request_url.join(plugin_key + "-key")
    response = requests.delete(request_url.url)
    if response.status_code == 204:
        return True
    return False


def module_status(previous_request: dict) -> typing.Tuple[int, int, typing.List['ModuleDto']]:
    """ Returns the module status of an plugin based on a request/dict containing an PluginDto
    returns an tuple containing
        1. number of all plugins
        2. number of enabled plugins
        3. Array of disabled plugins
    """
    plugin_dto = PluginDto.decode(previous_request)
    all_modules = 0
    enabled_modules = 0
    disabled_modules = []
    for module in plugin_dto.modules:
        all_modules += 1
        if module.enabled:
            enabled_modules += 1
        else:
            disabled_modules.append(module)
    return all_modules, enabled_modules, disabled_modules


def get_safemode(base_url: furl) -> bool:
    request_url = base_url.copy()
    request_url.add(path=UPM_API_ENDPOINT)
    request_url.add(path="safe-mode")
    response = requests.get(request_url.url)
    return response.json().get("enabled")


def enable_disable_safemode(base_url: furl, enable: bool, keepState: bool = False) -> bool:
    headers = {"Content-Type": "application/vnd.atl.plugins.safe.mode.flag+json"}
    data = {
        "enabled": enable,
        "links": {},
    }

    request_url = base_url.copy()
    request_url.add(path=UPM_API_ENDPOINT)
    request_url.add(path="safe-mode")
    request_url.add(query_params={"keepState": "true" if keepState else "false"})
    response = requests.put(request_url.url,
                            headers=headers,
                            json=data)
    response_json = response.json()
    return "subCode" not in response_json and response_json["enabled"] == enable
