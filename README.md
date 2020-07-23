## pluploader

[![PyPI version](https://badge.fury.io/py/pluploader.svg)](https://badge.fury.io/py/pluploader)

A simple command line plugin uploader/installer/manager for atlassian product 
server instances (Confluence/Jira) written in python(3).

## Installation

Regulary tested on Linux (Arch Linux), MacOS and Windows 10.

There are two ways to install this repository:

### pip 

```
pip3 install pluploader
```

### manual

Clone this repository and then run:

```
pip3 install . --user
```

OR

```
python setup.py install
```

## Usage

### Configuration

If you don't want to write the username or password (or any other parameter)
each time, you can use a filed called `.pluprc`, either placed in your current
maven project or/and in your homedirectory. A example looks like this:

```
host: localhost
port: 8090
user: admin
password: admin
```

Then, you can upload a plugin by just typing:

```
pluploader
```

### Uploading plugins

If you are in a maven project, the basic usage is fairly simple. Just type:

```
pluploader --user admin --password admin
```

The pluploader then uploads and enables the current artifact specified in the 
pom.xml


If you are not in a maven directory currently, but you want to upload a specific
file, you can also use the `-f plugin.jar` flag.

If you want to confirm your upload, you can also use the `-i` / 
`--interactive` flag.

It is recommended to use the pluploader with maven. The usage looks like:

```
atlas-mvn clean install && pluploader
```

### Managing plugins

pluploader can also replace the usage of the universal plugin manager completely
by using the subcommands `list`, `info`, `enable`, `disable`, and `uninstall`.

To get a list of all installed plugins of the configured instance, just type:

```bash
pluploader list
```

A green checkmark indicates that the plugin is enabled, while a exclamation mark
indicates that the plugin is disabled.


In order to retrieve more information about a specific plugin, you can use the
command `info`.

```
pluploader info com.example.plugin.key
```

The plugin key can be omitted in a maven directory, if the parameter
`atlassian.plugin.key` is set in plaintext.

The commands `enable`, `disable` or `uninstall` follow the same syntax.


## FAQ

### Why would I use the pluploader over X?

Of course, you can use whatever tool you want to. 

### Why would I use the pluploader over the UPM?

It's a faster workflow.

### Why would I use the pluploader over the Atlas-CLI?

atlas-cli is awesome, but sadly it's deprecated. Also since you can use your own
maven command with pluploader, you therefore can skip tests, make a mvn clean,
and many more.

In general, pluploader is just a bit more flexiable.

### Why would I use the pluploader over QuickReload?

QuickReload is cool, but some of us prefer to use docker instances or atlas-standalone
rather than atlas-run.
