""" This module provides a basic interface for the upm rest api
"""

import dataclasses
import json
import typing

import requests
from colorama import Fore
from furl import furl
from packaging import version


@dataclasses.dataclass()
class ModuleDto:
    completeKey: str
    key: typing.Optional[str]
    name: str
    enabled: bool
    optional: bool
    recognisableType: bool
    broken: bool

    @classmethod
    def decode(cls, obj: dict) -> "ModuleDto":
        if "key" in obj:
            return cls(
                key=obj.get("key"),
                completeKey=obj.get("completeKey", ""),
                name=obj.get("name", ""),
                enabled=obj.get("enabled", False),
                optional=obj.get("optional", False),
                recognisableType=obj.get("recognisableType", False),
                broken=obj.get("broken", True),
            )
        raise ValueError("decode expected passed object to have a key.")


@dataclasses.dataclass()
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
                        if module.enabled:
                            status = f"{Fore.GREEN}✓{Fore.RESET}"
                        else:
                            status = f"{Fore.YELLOW}!{Fore.RESET}"
                        print(f"  {status} {module.name[:20]:20} {module.key}")
            else:
                print(f"{(key + ':'):15} {value}")

    @classmethod
    def decode(cls, obj: dict) -> "PluginDto":
        if "key" in obj:
            return cls(
                key=obj.get("key"),
                name=obj.get("name", ""),
                version=obj.get("version", "0.0.1"),
                userInstalled=obj.get("userInstalled", False),
                enabled=obj.get("enabled", False),
                description=obj.get("description", ""),
                modules=[ModuleDto.decode(x) for x in obj.get("modules", [])],
            )
        raise ValueError("decode expected passed object to have a key.")


@dataclasses.dataclass()
class License:
    plugin_key: str
    valid: bool
    error: typing.Optional[str]
    evaluation: bool
    nearly_expired: bool
    maximum_number_of_users: typing.Optional[int]
    license_type: str
    expiry_date: typing.Optional[int]
    raw_license: typing.Optional[str]
    active: typing.Optional[bool]
    cloud_SEN: typing.Optional[str]
    cloud_auto_renewal: typing.Optional[str]

    @classmethod
    def decode(cls, obj: dict) -> "License":
        if "valid" in obj:
            return cls(
                plugin_key=obj.get("pluginKey"),
                valid=obj.get("valid"),
                error=obj.get("error", None),
                evaluation=obj.get("evaluation"),
                nearly_expired=obj.get("nearlyExpired"),
                maximum_number_of_users=obj.get("maximumNumberOfUsers", None),
                license_type=obj.get("licenseType"),
                expiry_date=obj.get("expiryDate", None),
                raw_license=obj.get("rawLicense"),
                active=obj.get("active", None),
                cloud_SEN=obj.get("supportEntitlementNumber", None),
                cloud_auto_renewal=obj.get("autoRenewal", None),
            )
        raise ValueError('decode expected passed object to have a "rawLicense" field.')


class UpmApi:
    UPM_API_ENDPOINT: str = "/rest/plugins/1.0/"

    def __init__(self, base_url: furl):
        self.base_url: furl = base_url

    def get_token(self) -> str:
        """ Get token from api endpoint
        """
        token_url: furl = self.base_url.copy()
        token_url.add(path=self.UPM_API_ENDPOINT)
        token_url.set(args={"os_authType": "basic"})
        token_response = requests.head(token_url.url)
        token = token_response.headers["upm-token"]
        return token

    def upload_plugin(self, files: typing.Dict[str, typing.BinaryIO], token: str) -> typing.Tuple[int, typing.Any]:
        """ Upload plugin
        """
        upload_url = self.base_url.copy()
        upload_url.set(args={"token": token})
        upload_url.add(path=self.UPM_API_ENDPOINT)
        upload_response = requests.post(upload_url.url, files=files)
        text = upload_response.text.replace("<textarea>", "").replace("</textarea>", "")
        upload_response_data = json.loads(text)
        progress = int(upload_response_data.get("status", {}).get("amountDownloaded", 0))
        return progress, upload_response_data

    def get_current_progress(self, previous_request) -> typing.Tuple[int, typing.Dict]:
        progress_url = self.base_url.copy()
        progress_url.set(path=previous_request["links"]["self"])
        progress_rd = requests.get(progress_url.url).json()
        if "type" in progress_rd:
            progress = int(progress_rd.get("status", {}).get("amountDownloaded", 0))
            return progress, progress_rd
        return 100, progress_rd

    def get_all_plugins(self, user_installed: bool = True) -> typing.List[PluginDto]:
        """ Gets a list of all installed plugins from the api and returns it
        If user_installed is set true (default), only user installed plugins are listed
        """
        request_url = self.base_url.copy()
        request_url.add(path=self.UPM_API_ENDPOINT)
        response = requests.get(request_url.url)
        return_obj = [PluginDto.decode(x) for x in response.json().get("plugins", [])]
        if user_installed:
            return_obj = filter(lambda x: x.userInstalled, return_obj)
        return return_obj

    def get_plugin(self, plugin_key: str) -> PluginDto:
        """ Gets Plugin info by using the UPM_API_ENDPOINT/plugin-key/ endpoint and
        returns it as a PluginDto
        """
        request_url = self.base_url.copy()
        request_url.add(path=self.UPM_API_ENDPOINT)
        request_url.join(plugin_key + "-key")
        response = requests.get(request_url.url)
        return_obj = PluginDto.decode(response.json())
        return return_obj

    def enable_disable_plugin(self, plugin_key: str, enabled: bool) -> PluginDto:
        """ Enables/Disables Plugin"""
        mod = {"enabled": enabled}
        return self._modify_plugin(plugin_key, mod)

    def _modify_plugin(self, plugin_key: str, modifications: dict) -> PluginDto:
        """ Puts Changes to plugin by using the UPM_API_ENDPOINT/plugin-key/ endpoint and
        returns new infos as a PluginDto
        """
        request_url = self.base_url.copy()
        request_url.add(path=self.UPM_API_ENDPOINT)
        request_url.join(plugin_key + "-key")
        headers = {"Content-Type": "application/vnd.atl.plugins.plugin+json"}
        response = requests.put(request_url.url, json=modifications, headers=headers)
        return_obj = PluginDto.decode(response.json())
        return return_obj

    def uninstall_plugin(self, plugin_key: str) -> bool:
        """ Uninstalls a plugin by using the UPM_API_ENDPOINT/plugin-key/ endpoint
        """
        request_url = self.base_url.copy()
        request_url.add(path=self.UPM_API_ENDPOINT)
        request_url.join(plugin_key + "-key")
        response = requests.delete(request_url.url)
        return response.status_code == 204

    def module_status(self, previous_request: dict,) -> typing.Tuple[int, int, typing.List[ModuleDto]]:
        """ Returns the module status of an plugin based on a request/dict containing an PluginDto
        returns an tuple containing
            1. number of all plugins
            2. number of enabled plugins
            3. Array of disabled plugins
        """
        plugin_dto = PluginDto.decode(previous_request)
        disabled_modules = [module for module in plugin_dto.modules if not module.enabled]
        all_modules = len(plugin_dto.modules)
        enabled_modules = all_modules - len(disabled_modules)
        return all_modules, enabled_modules, disabled_modules

    def get_safemode(self) -> bool:
        request_url = self.base_url.copy()
        request_url.add(path=self.UPM_API_ENDPOINT)
        request_url.add(path="safe-mode")
        response = requests.get(request_url.url)
        return response.json()["enabled"]

    def enable_disable_safemode(self, enable: bool, keepState: bool = False) -> bool:
        headers = {"Content-Type": "application/vnd.atl.plugins.safe.mode.flag+json"}
        data = {
            "enabled": enable,
            "links": {},
        }

        request_url = self.base_url.copy()
        request_url.add(path=self.UPM_API_ENDPOINT)
        request_url.add(path="safe-mode")
        request_url.add(query_params={"keepState": "true" if keepState else "false"})
        response = requests.put(request_url.url, headers=headers, json=data)
        response_json = response.json()
        return "subCode" not in response_json and response_json["enabled"] == enable

    def get_license(self, plugin_key: str) -> License:
        request_url = self.base_url.copy()
        request_url.add(path=self.UPM_API_ENDPOINT)
        request_url.add(path=plugin_key + "-key")
        request_url.add(path="license")
        response = requests.get(request_url.url)
        return License.decode(response.json())

    def update_license(self, plugin_key: str, raw_license: str):
        request_url = self.base_url.copy()
        request_url.add(path=self.UPM_API_ENDPOINT)
        request_url.add(path=plugin_key + "-key")
        request_url.add(path="license")
        headers = {"Content-Type": "application/vnd.atl.plugins+json"}
        try:
            response = requests.put(request_url.url, json={"rawLicense": raw_license}, headers=headers)
            return License.decode(response.json())
        except Exception:
            raise ValueError(response.status_code, response.content)

    def delete_license(self, plugin_key: str):
        request_url = self.base_url.copy()
        request_url.add(path=self.UPM_API_ENDPOINT)
        request_url.add(path=plugin_key + "-key")
        request_url.add(path="license")
        response = requests.delete(request_url.url)
        return License.decode(response.json())
