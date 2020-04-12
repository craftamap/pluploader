## pluploader

A simple command line plugin uploader/installer for atlassian product server 
instances (Confluence/Jira) written in python(3).

## Installation

Currently, just Unix-based systems are supported.
There are two ways to install this repository:

### pip 

As we are not on PyPi (yet), you can currently install with this command:

```
pip3 install git+https://github.com/livelyapps/pluploader.git --user
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

If you are in a maven project, the basic usage is fairly simple. Just type:

```
pluploader --user admin --password admin
```

The pluploader then uploads and enables the current artifact specified in the 
pom.xml

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

If you are not in a maven directory currently, but you want to upload a specific
file, you can also use the `-f plugin.jar` flag.

If you want to confirm your upload, you can also use the `-i` / 
`--interactive` flag.

It is recommended to use the pluploader with maven. The usage looks like:

```
atlas-mvn clean install && pluploader
```

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
