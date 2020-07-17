""" This module provides some basic path tools for the pluploader cli tool
"""

import typing
import os
import os.path
import xml.etree.ElementTree as ET


def get_jar_from_pom() -> typing.BinaryIO:
    """ Get jar to upload based on maven pom

    This function reads the pom and analyses which artifact was build by the last
    `mvn package` command. If the file exists, the file will be returned
    """
    rootdir = find_maven_project_root(".")
    namespace = {"ns": "http://maven.apache.org/POM/4.0.0"}

    root = ET.parse(f'{rootdir}/pom.xml').getroot()
    artifact_id = root.find("ns:artifactId", namespace).text
    version = root.find("ns:version", namespace).text

    filepath = os.path.join(rootdir, "target", f"{artifact_id}-{version}.jar")
    return open(filepath, "rb")


def get_plugin_key_from_pom() -> str:
    """ Get Plugin key from Pom.xml

    This function reads the pom and analyses which plugin will be built.
    """
    rootdir = find_maven_project_root(".")
    namespace = {"ns": "http://maven.apache.org/POM/4.0.0"}
    if os.path.isfile(f'{rootdir}/pom.xml'):
        try:
            root = ET.parse(f'{rootdir}/pom.xml').getroot()
            properties = root.find("ns:properties", namespace)
            plugin_id = properties.find("ns:atlassian.plugin.key",
                                        namespace).text
            return plugin_id
        except:
            return None
    else:
        return None


def find_maven_project_root(
        working_path: os.PathLike = ".") -> typing.Union[os.PathLike, bool]:
    """Tries to find a maven project root directory.

    Tries to find a maven project root directory if the current path is a
    parent directory. Works by finding the pom.xml file.
    Args:
        working_path: a string representation of the directory you want to find
            the project
    Returns:
        the absolute project path
    """
    project_root = False
    for walk_tuple in _walk_up(working_path):
        if "pom.xml" in walk_tuple[2]:
            project_root = walk_tuple[0]
            break
    return project_root


def _walk_up(
        start_path: os.PathLike = "."
) -> typing.Tuple[os.PathLike, typing.Tuple[os.PathLike],
                  typing.Tuple[os.PathLike]]:
    """ Generator for walking up a file path. os.walk like behavior

    Args: start_path: a os.PathLike path to start from

    Yields:
        3-Tuple (dirpath, dirnames, filenames)
    """
    current_path_split = os.path.split(os.path.abspath(start_path))
    while True:
        walk_tuple = next(os.walk(os.path.join(*current_path_split)))
        yield walk_tuple
        if current_path_split[1] == '':
            return
        current_path_split = os.path.split(current_path_split[0])
