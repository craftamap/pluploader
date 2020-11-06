""" Simple implementation to access endpoints of
    https://marketplace.atlassian.com/rest/2
"""

import dataclasses

import requests
import typing
from furl import furl
from .extensions import MpacAppVersionNotFoundError

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


def get_app_version(addonKey: str, version: str = "latest", hosting: str = "server"):
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
