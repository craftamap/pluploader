""" this module helps interacting with .jar-files built working for atlassian
server applications.
"""

import pathlib
from zipfile import ZipFile

from bs4 import BeautifulSoup

from .pathutil import PluginKeyNotFoundError


def _get_atlassian_plugin_xml_from_jar_path(path: pathlib.Path) -> str:
    """ Opens the jar on the provided path and tries to find the
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


def _find_plugin_key(atlassian_plugin_xml: str) -> str:
    """ Finds the plugin key in an atlassian_plugin_xml
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
    """ Tries to find the plugin key of an atlassian server app plugin by providing an path to the jar.
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
    return _find_plugin_key(atlas_xml)
