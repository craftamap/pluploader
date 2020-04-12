""" This module provides a basic interface for the upm rest api
"""

import typing
import dataclasses
import json
import inspect
from furl import furl
import requests
from requests.auth import HTTPBasicAuth
from packaging import version

PATH = "/rest/plugins/1.0/"


@dataclasses.dataclass
class RequestBase():
    """ This simple dataclass contains the elements to create the baseurl
    """
    host: str
    port: int
    user: str
    password: str
    scheme: str = "http"


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

    def print_table(self):
        """Prints table view of plugin information
        """
        for key, value in self.__dict__.items():
            print(f"{key:20}: {value}")

    @classmethod
    def from_dict(cls, env):
        """ creates PluginDto from a dict and ignores unknown keys
        """
        return cls(**{
            k: v
            for k, v in env.items() if k in inspect.signature(cls).parameters
        })

    @staticmethod
    def decode(obj: dict) -> typing.Union['PluginDto', dict]:
        if "name" in obj \
        and "key" in obj \
        and "version" in obj \
        and "enabled" in obj \
        and "userInstalled" in obj \
        and "description" in obj:
            return PluginDto.from_dict(obj)
        return obj


def get_token(request_base: RequestBase) -> str:
    """ Get token from api endpoint
    """
    token_url = furl()
    token_url.set(scheme=request_base.scheme,
                  host=request_base.host,
                  port=request_base.port,
                  path=PATH)
    token_url.set(args={"os_authType": "basic"})
    token_response = requests.head(token_url.url,
                                   auth=HTTPBasicAuth(request_base.user,
                                                      request_base.password))
    token = token_response.headers['upm-token']
    return token


def upload_plugin(request_base: RequestBase, files: typing.Dict,
                  token: str) -> str:
    """ Upload plugin
    """
    upload_url = furl()
    upload_url.set(scheme=request_base.scheme,
                   host=request_base.host,
                   port=request_base.port,
                   path=PATH)
    upload_url.set(args={"token": token})
    upload_response = requests.post(upload_url.url,
                                    files=files,
                                    auth=HTTPBasicAuth(request_base.user,
                                                       request_base.password))
    text = upload_response.text.replace("<textarea>",
                                        "").replace("</textarea>", "")
    upload_response_data = json.loads(text)
    progress = int(
        upload_response_data.get("status", {}).get("amountDownloaded", 0))
    return (progress, upload_response_data)


def get_current_progress(request_base: RequestBase,
                         previous_request) -> (int, typing.Dict):
    progress_url = furl()
    progress_url.set(scheme=request_base.scheme,
                     host=request_base.host,
                     port=request_base.port,
                     path=previous_request["links"]["self"])
    progress_rd = requests.get(
        progress_url.url,
        auth=HTTPBasicAuth(request_base.user, request_base.password)).json()
    if "type" in progress_rd:
        progress = int(
            progress_rd.get("status", {}).get("amountDownloaded", 0))
        return (progress, progress_rd)
    return (100, progress_rd)


def get_all_plugins(request_base: RequestBase,
                    user_installed: bool = True) -> typing.List['PluginDto']:
    """ Gets a list of all installed plugins from the api and returns it
    If user_installed is set true (default), only user installed plugins are listed
    """
    request_url = furl()
    request_url.set(scheme=request_base.scheme,
                    host=request_base.host,
                    port=request_base.port,
                    path=PATH)
    response = requests.get(request_url.url,
                            auth=HTTPBasicAuth(request_base.user,
                                               request_base.password))
    return_obj = response.json(object_hook=PluginDto.decode)["plugins"]
    if user_installed:
        return_obj = filter(lambda x: x.userInstalled, return_obj)
    return return_obj


def get_plugin(request_base: RequestBase, plugin_key: str) -> 'PluginDto':
    """ Gets Plugin info by using the PATH/plugin-key/ endpoint and
    returns it as a PluginDto
    """
    request_url = furl()
    request_url.set(scheme=request_base.scheme,
                    host=request_base.host,
                    port=request_base.port,
                    path=PATH)
    request_url.join(plugin_key + "-key")
    response = requests.get(request_url.url,
                            auth=HTTPBasicAuth(request_base.user,
                                               request_base.password))
    return_obj = response.json(object_hook=PluginDto.decode)
    return return_obj


def enable_disable_plugin(request_base: RequestBase, plugin_key: str,
                          enabled: bool) -> 'PluginDto':
    """ Enables/Disables Plugin"""
    mod = {"enabled": enabled}
    return _modify_plugin(request_base, plugin_key, mod)


def _modify_plugin(request_base: RequestBase, plugin_key: str,
                   modifications: dict) -> 'PluginDto':
    """ Puts Changes to plugin by using the PATH/plugin-key/ endpoint and
    returns new infos as a PluginDto
    """
    request_url = furl()
    request_url.set(scheme=request_base.scheme,
                    host=request_base.host,
                    port=request_base.port,
                    path=PATH)
    request_url.join(plugin_key + "-key")
    headers = {"Content-Type": "application/vnd.atl.plugins.plugin+json"}
    response = requests.put(request_url.url,
                            auth=HTTPBasicAuth(request_base.user,
                                               request_base.password),
                            json=modifications,
                            headers=headers)
    return_obj = response.json(object_hook=PluginDto.decode)
    return return_obj

def uninstall_plugin(request_base: RequestBase, plugin_key: str) -> bool:
    """ Uninstalls a plugin by using the PATH/plugin-key/ endpoint
    """
    request_url = furl()
    request_url.set(scheme=request_base.scheme,
                    host=request_base.host,
                    port=request_base.port,
                    path=PATH)
    request_url.join(plugin_key + "-key")
    response = requests.delete(request_url.url,
                            auth=HTTPBasicAuth(request_base.user,
                                               request_base.password))
    if response.status_code == 204:
        return True
    return False
