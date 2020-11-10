""" Simple implementation to access endpoints of
    https://marketplace.atlassian.com/rest/2
"""

import dataclasses
import typing

import requests
from furl import furl

from .exceptions import MpacAppVersionNotFoundError

BASE_URL = furl("https://marketplace.atlassian.com/rest/2")


@dataclasses.dataclass()
class AddonVersion:
    @dataclasses.dataclass()
    class Link:
        href: furl
        type: str

        @classmethod
        def decode(cls: typing.ClassVar["AddonVersion.Link"], obj: typing.Dict[str, typing.Any]) -> "AddonVersion.Link":
            return cls(href=furl(obj.get("href")), type=obj.get("type"))

    @dataclasses.dataclass()
    class AddonVersionLinks:
        artifact: "AddonVersion.Link"
        alternate: "AddonVersion.Link"

        @classmethod
        def decode(cls: typing.ClassVar["AddonVersion.AddonVersionLinks"], obj: dict) -> "AddonVersion.AddonVersionLinks":
            return cls(
                artifact=AddonVersion.Link.decode(obj.get("artifact")),
                alternate=AddonVersion.Link.decode(obj.get("alternate")),
            )

    build_number: int
    name: str
    status: str
    payment_model: str
    links: "AddonVersion.AddonVersionLinks"

    @classmethod
    def decode(cls: typing.ClassVar["AddonVersion"], obj: typing.Dict[str, typing.Any]) -> "AddonVersion":
        return cls(
            build_number=obj.get("buildNumber"),
            name=obj.get("name"),
            status=obj.get("status"),
            payment_model=obj.get("paymentModel"),
            links=cls.AddonVersionLinks.decode(obj.get("_links")),
        )


@dataclasses.dataclass
class Asset:
    @dataclasses.dataclass
    class AssetFileInfo:
        logical_file_name: str
        size: str

        @classmethod
        def decode(cls: typing.ClassVar["Asset.AssetFileInfo"], obj: typing.Dict[str, typing.Any]) -> "Asset.AssetFileInfo":
            return cls(logical_file_name=obj.get("logicalFileName"), size=obj.get("size"))

    @dataclasses.dataclass
    class AssetLink:
        href: furl

        @classmethod
        def decode(cls: typing.ClassVar["Asset.AssetLink"], obj: typing.Dict[str, typing.Any]) -> "Asset.AssetLink":
            return cls(href=furl(obj.get("href")))

    links: typing.Dict[str, AssetLink]
    file_info: AssetFileInfo

    @classmethod
    def decode(cls: typing.ClassVar["Asset"], obj: typing.Dict[str, typing.Any]) -> "Asset":
        return cls(
            links={k: cls.AssetLink.decode(v) for (k, v) in obj.get("_links").items()},
            file_info=cls.AssetFileInfo.decode(obj.get("fileInfo")),
        )


def get_app_version(addonKey: str, version: str = "latest", hosting: str = "server") -> AddonVersion:
    """ Choosing "server" as default hosting option for now... We propably need to change this
    in 2022?, when you people will stop publishing server versions
    """
    url: furl
    if version == "latest":
        url = BASE_URL / f"addons/{addonKey}/versions/{version}"
    else:
        url = BASE_URL / f"addons/{addonKey}/versions/name/{version}"
    url.args["hosting"] = hosting
    response = requests.get(url)

    if not response.ok:
        raise MpacAppVersionNotFoundError(url)

    return AddonVersion.decode(response.json())


def get_binary_from_app_version(addon_version: AddonVersion) -> Asset:
    url: furl = addon_version.links.artifact.href.copy()
    url.set(origin=BASE_URL.origin)
    response = requests.get(url)

    if not response.ok:
        raise MpacAppVersionNotFoundError(url)

    return Asset.decode(response.json())
