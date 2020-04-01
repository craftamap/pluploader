import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pluploader",
    version="0.0.1",
    author="Fabian Siegel, Scandio GmbH",
    author_email="fabian.siegel@scandio.de",
    description="CLI Confluence/Jira Plugin uploader",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://git.scandio.de/users/fsiegel/repos/sc-pluploader/browse",
    packages=setuptools.find_packages(),
    entry_points={
        "console_scripts": ["pluploader=scripts.pluploader:main"],
    }
)
