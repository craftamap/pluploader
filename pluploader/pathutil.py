""" This module provides some basic path tools for the pluploader cli tool
"""

import os
import pathlib
import typing
import xml.etree.ElementTree as ET


class PluginKeyNotFoundError(RuntimeError):
    pass


def get_jar_path_from_pom() -> os.PathLike:
    """ Get jar to upload based on maven pom

    This function reads the pom and analyses which artifact was build by the last
    `mvn package` command. If the file exists, the file will be returned
    """
    rootdir = find_maven_project_root()
    namespace = {"ns": "http://maven.apache.org/POM/4.0.0"}

    root = ET.parse(f"{rootdir}/pom.xml").getroot()
    artifact_id = root.find("ns:artifactId", namespace).text
    version = root.find("ns:version", namespace).text

    return rootdir / "target" / f"{artifact_id}-{version}.jar"


def get_plugin_key_from_pom() -> str:
    """ Get Plugin key from Pom.xml

    This function reads the pom and analyses which plugin will be built.
    """
    try:
        rootdir = find_maven_project_root()
        namespace = {"ns": "http://maven.apache.org/POM/4.0.0"}
        root = ET.parse(f"{rootdir}/pom.xml").getroot()
        properties = root.find("ns:properties", namespace)
        plugin_id = properties.find("ns:atlassian.plugin.key", namespace).text
        return plugin_id
    except FileNotFoundError as exc:
        raise exc
    except Exception as exc:
        raise PluginKeyNotFoundError(exc)


def find_maven_project_root(working_path: pathlib.Path = pathlib.Path(".")) -> pathlib.Path:
    """Tries to find a maven project root directory.

    Tries to find a maven project root directory if the current path is a
    parent directory. Works by finding the pom.xml file.
    Args:
        working_path: a string representation of the directory you want to find
            the project
    Returns:
        the absolute project path
    """
    for walk_tuple in _walk_up(working_path):
        if "pom.xml" in walk_tuple[2]:
            return walk_tuple[0]
    raise FileNotFoundError()


def _walk_up(
    start_path: pathlib.Path = pathlib.Path(),
) -> typing.Tuple[pathlib.Path, typing.Tuple[os.PathLike], typing.Tuple[os.PathLike]]:
    """ Generator for walking up a file path. os.walk like behavior

    Args: start_path: a os.PathLike path to start from

    Yields:
        3-Tuple (dirpath, dirnames, filenames)
    """
    current_path = start_path.resolve()
    while True:
        walk_tuple = (
            current_path,
            [x.name for x in current_path.resolve().iterdir() if x.is_dir()],
            [x.name for x in current_path.resolve().iterdir() if not x.is_dir()],
        )
        yield walk_tuple
        if current_path == pathlib.Path(current_path.root):
            return
        current_path = current_path.parent
