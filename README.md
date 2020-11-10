# pluploader

![PyPI version](https://img.shields.io/pypi/v/pluploader?style=flat-square) ![Upload Python Package](https://img.shields.io/github/workflow/status/livelyapps/pluploader/Python%20package/master?style=flat-square)

A simple command line plugin uploader/installer/manager for atlassian product
server instances (Confluence/Jira) written in python(3).

## Installation

Regulary tested on Linux (Arch Linux), MacOS and Windows 10.

### pip (recommended)

```bash
pip3 install pluploader
```

### Docker

If you do not want to install python3 or pip, you can also pull the latest
docker image from dockerhub or github:

```bash
docker pull craftamap/pluploader:latest
# OR
docker pull docker.pkg.github.com/livelyapps/pluploader/pluploader:latest
```

pluploader can then be run by executing

```bash
docker run -v "$(pwd)":/workdir -it craftamap/pluploader:v0.4.1
```

## Usage

For a in-depth explanation, see `pluploader --help`

> ℹ This documentation describes the master branch, and not (necessarily) the latest release.

### Global Options

You can specify various global options:

- `--base-url <base-url>`, default: `http://localhost:8090`
- `--user <username>`, default: `admin`
- `--password <password>`, default: `admin`  
  If you do not want to put your password in the command line plaintext, you can
  also use...
- `--ask-for-password`

All Global Options can be overwritten by using a configuration file. See more in
[Configuration](#Configuration)

### Uploading plugins

If you are in a maven project, the basic usage is fairly simple. Just type:

```bash
pluploader --user admin --password admin
```

The pluploader then uploads and enables the current artifact specified in the
pom.xml

If you are not in a maven directory currently, but you want to upload a specific
file, you can also use the `-f plugin.jar` flag.

If you want to confirm your upload, you can also use the `-i` /
`--interactive` flag.

It is recommended to use the pluploader with maven. The usage looks like:

```bash
atlas-mvn clean package && pluploader
```

#### Installing apps from the marketplace

pluploader supports downloading apps from the atlassian marketplace to your local
machine and installing them afterwards. You need to supply either `--mpac-key`,
which is the normal addon-key, or `--mpac-id` (experimental), which is the
numeric id of an marketplace id (72307 https://marketplace.atlassian.com/apps/72307)

```bash
pluploader --mpac-key com.atlassian.confluence.extra.team-calendars
```

**NOTE**:
If you specify one of the global options, you need to add the `install`-command:

```bash
pluploader --base-url https://your-confluence.com:8090 install
```

You can work around this by using the configuration file or by using environment variables.

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

```bash
pluploader info com.example.plugin.key
```

The plugin key can be omitted in a maven directory, if the parameter
`atlassian.plugin.key` is set in plaintext.

The commands `enable`, `disable` or `uninstall` follow the same syntax.

### Safe Mode

pluploader also supports disabling or enabling all apps using Safe Mode.

To retrieve the status if safe-mode is enabled at the moment, use

```bash
pluploader safe-mode status
```

You can enable and disable safe mode by using

```bash
pluploader safe-mode enable
```

And

```bash
pluploader safe-mode disable
# OR
pluploader safe-mode disable --keep-state
```

### Licenses (Beta)

You can also use the pluploader to get and set licenses for your plugins.

To get the current license information:

```bash
pluploader license info com.example.plugin.key
```

To set a lciense, use the `update` functionality.

```bash
pluploader license update com.example.plugin.key --license "AAA..."
```

> ℹ Pro tip: Use `xargs` to read a license from a file by using
>
> ```bash
> cat license.txt | xargs pluploader license update --license
> ```

You can also apply [timebomb licenses](https://developer.atlassian.com/platform/marketplace/timebomb-licenses-for-testing-server-apps/)

by using

```bash
pluploader license timebomb com.example.plugin.key --timebomb threehours
```

You can choose between 3 hours (threehours), 60 seconds (sixtyseconds) and
10 seconds (tenseconds)

To remove an applied license, you can use:

```bash
pluploader license delete com.example.plugin.key
```

### Scheduled Jobs (Confluence - Experimental)

> ℹ This feature is currently experimental and only works in specific version of
> Confluence (tested on Confluence 7.5).

Pluploader can also be used to retrieve information about confluence jobs and
execute them.

You can grab a list of all jobs by running

```bash
pluploader job list
```

Available options are:

- `--hide-default` - Hides confluence internal jobs
- `--print-all-infos` - print more informations

You can also run jobs by running

```bash
pluploader job run
```

Get more information about a job by running

```bash
pluploader job info
```

And disable or enable jobs by running

```bash
pluploader job enable
# AND
pluploader job disable
```

A job can be specified by either using `--id <job id>` or by using
`--idx <job index in list>`. If no job is specified, you will be asked
interactively.

### Configuration

If you don't want to write the username or password (or any other global
parameter) each time, you can use a filed called `.pluprc`, either placed in
your current maven project or/and in your home directory. A example looks like
this:

```bash
base_url: https://example.com:8090
user: admin
password: admin
```

### Environment variables

You can also specify username, password and base url by using `PLUP_USER`,
`PLUP_PASSWORD` and `PLUP_BASEURL`.

## Development

pluploader uses [poetry](https://python-poetry.org/) as it's package manager. As a command line argument parser, [Typer](https://typer.tiangolo.com/) is used.

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
