import os
import pathlib
import tempfile

import requests
from furl import furl

from . import scraper
from . import rest


def _download_file_to_tmp_dir(url: furl) -> os.PathLike:
    response = requests.get(url)
    response_url: furl = furl(response.url)

    temp_dir = pathlib.Path(tempfile.gettempdir())

    pluploader_temp_dir = temp_dir / "pluploader"
    pluploader_temp_dir.mkdir(exist_ok=True)

    filename = pluploader_temp_dir / response_url.path.segments[-1].split("/")[-1]

    print(filename)
    with open(filename, "wb") as tmpfile:
        tmpfile.write(response.content)
    return filename


def download_app_by_app_key(app_key: str, version: str = "latest") -> os.PathLike:
    app = rest.get_app_version(app_key, version)
    download_link = app.links.artifact.href
    download_link.origin = "https://marketplace.atlassian.com"
    return _download_file_to_tmp_dir(download_link)


def download_app_by_marketplace_id(marketplace_id: int, version: str = "latest") -> os.PathLike:
    download_link = scraper.download_link_by_marketplace_id(marketplace_id, version)
    return _download_file_to_tmp_dir(download_link)
