""" this module helps interacting with .jar-files built working for atlassian
server applications.
"""

import pathlib
from dataclasses import dataclass
from typing import IO
from zipfile import ZipFile

from bs4 import BeautifulSoup

from .pathutil import PluginKeyNotFoundError


def _get_atlassian_plugin_xml_from_jar_bytes(jar_bytes: IO[bytes]) -> str:
    """Opens the jar on the provided path and tries to find the
    atlassian-plugin.xml in this file
    Args:
        path (pathlib.Param): the path to the jar file
    Returns:
        str: the content of atlassian_plugin.xml

    Raises:
        FileNotFoundError: If the file of path is not found
        zipfile.BadZipFile: If the provided file of path is not a zip file
        KeyError: If no atlassian_plugin.xml is existing inside the zip/jar
    """
    with ZipFile(jar_bytes) as jar:
        with jar.open("atlassian-plugin.xml") as atlassian_plugin_xml:
            return atlassian_plugin_xml.read()


def _get_atlassian_plugin_xml_from_jar_path(path: pathlib.Path) -> str:
    """Opens the jar on the provided path and tries to find the
    atlassian-plugin.xml in this file
    Args:
        path (pathlib.Param): the path to the jar file
    Returns:
        str: the content of atlassian_plugin.xml

    Raises:
        FileNotFoundError: If the file of path is not found
        zipfile.BadZipFile: If the provided file of path is not a zip file
        KeyError: If no atlassian_plugin.xml is existing inside the zip/jar
    """
    with ZipFile(path) as jar:
        with jar.open("atlassian-plugin.xml") as atlassian_plugin_xml:
            return atlassian_plugin_xml.read()


@dataclass(frozen=True)
class PluginXmlData:
    key: str
    name: str
    version: str


def _extract_data(atlassian_plugin_xml: str) -> PluginXmlData:
    """Extracts data from the atlassian_plugin_xml and returns a PluginXmlData
    Args:
        atlassian_plugin_xml: the content of an atlassian_plugin.xml
    """

    soup = BeautifulSoup(atlassian_plugin_xml, "xml")
    plugin_key = soup.find("atlassian-plugin").get("key")
    if plugin_key is None:
        raise PluginKeyNotFoundError()
    name = soup.find("atlassian-plugin").get("key")
    version = soup.find("version").string

    return PluginXmlData(plugin_key, name, version)


def _find_plugin_key(atlassian_plugin_xml: str) -> str:
    """Finds the plugin key in an atlassian_plugin_xml
    Args:
        atlassian_plugin_xml: the content of an atlassian_plugin.xml
    Returns:
        str: the plugin key of the provided atlassian_plugin.xml
    Raises:
        pluploader.pathutil.PluginKeyNotFoundError: If the PluginKey could not be found
    """
    soup = BeautifulSoup(atlassian_plugin_xml, "xml")
    key = soup.find("atlassian-plugin").get("key")
    if key is None:
        raise PluginKeyNotFoundError()
    return key


def get_plugin_key_from_jar_path(path: pathlib.Path) -> str:
    """Tries to find the plugin key of an atlassian server app plugin by providing the path to its jar.
    Args:
        path (pathlib.Param): the path to the jar file
    Returns:
        str: The Plugin Key
    Raises:
        FileNotFoundError: If the file of path is not found
        zipfile.BadZipFile: If the provided file of path is not a zip file
        KeyError: If no atlassian_plugin.xml is existing inside the zip/jar
        pluploader.pathutil.PluginKeyNotFoundError: If the PluginKey could not be found
    """
    atlas_xml = _get_atlassian_plugin_xml_from_jar_path(path)
    data = _extract_data(atlas_xml)
    return data.key


def get_plugin_info_from_jar_path(path: pathlib.Path) -> PluginXmlData:
    """Tries to find various information of an atlassian server app plugin by providing the path to its jar.
    Args:
        path (pathlib.Param): the path to the jar file
    Returns:
        PluginKeyData: The Plugin Key
    Raises:
        FileNotFoundError: If the file of path is not found
        zipfile.BadZipFile: If the provided file of path is not a zip file
        KeyError: If no atlassian_plugin.xml is existing inside the zip/jar
        pluploader.pathutil.PluginKeyNotFoundError: If the PluginKey could not be found
    """
    atlas_xml = _get_atlassian_plugin_xml_from_jar_path(path)
    return _extract_data(atlas_xml)


def _get_jar_from_obr_path(path: pathlib.Path) -> IO[bytes]:
    """Tries to find various information of an atlassian server app plugin by proving the path to a .obr-file
    Args:
        path (pathlib.Param): the path to the obr file
    Returns:
        PluginKeyData: The Plugin Key
    Raises:
        FileNotFoundError: If the file of path is not found
        zipfile.BadZipFile: If the provided file of path is not a zip file
        KeyError: If no atlassian_plugin.xml is existing inside the zip/jar
        pluploader.pathutil.PluginKeyNotFoundError: If the PluginKey could not be found
    """
    # let's open the obr, and look for a jar on the top-level
    with ZipFile(path) as obr:
        for file in obr.infolist():
            if not file.is_dir() and file.filename.endswith(".jar"):
                return obr.open(file.filename)
    raise FileNotFoundError()


def get_plugin_info_from_obr_path(path: pathlib.Path) -> PluginXmlData:
    jar_bytes = _get_jar_from_obr_path(path)
    atlas_xml = _get_atlassian_plugin_xml_from_jar_bytes(jar_bytes)
    return _extract_data(atlas_xml)
