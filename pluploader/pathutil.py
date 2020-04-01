""" This module provides some basic path tools for the pluploader cli tool
"""

import typing
import os
import os.path


def find_maven_project_root(working_path: os.PathLike = ".") -> typing.Union[os.PathLike,bool]:
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



def _walk_up(start_path: os.PathLike = ".") -> typing.Tuple[
        os.PathLike,
        typing.Tuple[os.PathLike],
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
