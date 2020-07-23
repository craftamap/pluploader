import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pluploader",
    version="0.3.0",
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
        "coloredlogs"
    ]
)
