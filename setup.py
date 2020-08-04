import setuptools
import subprocess

with open("README.md", "r") as fh:
    long_description = fh.read()

try:
    label = subprocess.check_output(["git", "describe", "--always", "--tags"]).strip()
except Exception:
    label = "UNKNOWN"


setuptools.setup(
    name="pluploader",
    version=label.decode("utf-8"),
    python_requires='>=3.6',
    author="Fabian Siegel, Lively Apps GmbH",
    author_email="fabian@livelyapps.com",
    description="CLI Confluence/Jira Plugin uploader",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/livelyapps/pluploader",
    packages=setuptools.find_packages(),
    entry_points={
        "console_scripts": ["pluploader=scripts.pluploader:main"],
    },
    install_requires=[
        "requests",
        "tqdm",
        "colorama",
        "configargparse",
        "furl",
        "PyYAML",
        "packaging",
        "coloredlogs",
        "importlib-metadata",
        "dataclasses"
    ]
)
