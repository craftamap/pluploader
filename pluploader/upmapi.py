""" This module provides a basic interface for the upm rest api
"""

import typing
import dataclasses
from furl import furl
import requests
from requests.auth import HTTPBasicAuth
import json

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

def get_token(request_base: RequestBase) -> str:
    """ Get token from api endpoint
    """
    token_url = furl()
    token_url.set(scheme=request_base.scheme, host=request_base.host,
                  port=request_base.port, path=PATH)
    token_url.set(args={"os_authType":"basic"})
    token_response = requests.head(token_url.url,
                                   auth=HTTPBasicAuth(request_base.user, request_base.password)
                                   )
    token = token_response.headers['upm-token']
    return token


def upload_plugin(request_base: RequestBase, files: typing.Dict, token: str) -> str:
    """ Upload plugin
    """
    upload_url = furl()
    upload_url.set(scheme=request_base.scheme, host=request_base.host,
                   port=request_base.port, path=PATH)
    upload_url.set(args={"token": token})
    upload_response = requests.post(upload_url.url, files=files,
                                    auth=HTTPBasicAuth(request_base.user, request_base.password)
                                    )
    text = upload_response.text.replace("<textarea>", "").replace("</textarea>", "")
    upload_response_data = json.loads(text)
    progress = int(upload_response_data.get("status", {}).get("amountDownloaded", 0))
    return (progress, upload_response_data)


def get_current_progress(request_base: RequestBase, previous_request) -> (int, typing.Dict):
    progress_url = furl()
    progress_url.set(scheme=request_base.scheme, host=request_base.host,
                     port=request_base.port,
                     path=previous_request["links"]["self"])
    progress_rd = requests.get(progress_url.url,
                               auth=HTTPBasicAuth(request_base.user, request_base.password)
                              ).json()
    if ("type" in progress_rd):
        progress = int(progress_rd.get("status", {}).get("amountDownloaded", 0))
        return (progress, progress_rd)
    return (100, progress_rd)
