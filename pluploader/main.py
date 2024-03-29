""" pluploader executable
"""
import json
import logging
import pathlib
import sys
import time
import typing
import zipfile
from xmlrpc import client as rpcclient
from xmlrpc.client import ProtocolError as RpcProtocolError

import furl
import requests
import typer
import yaml
from click_default_group import DefaultGroup
from packaging.version import parse as version_parse
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress
from rich.table import Table

from . import __version__
from .job import app_job
from .license import app_license
from .mpac import download
from .mpac.exceptions import MpacAppNotFoundError, MpacAppVersionNotFoundError
from .safemode import app_safemode
from .upm.upmapi import PluginDto, UpmApi
from .upm.upmcloudapi import UpmCloudApi
from .util import atlassian_jar as jar
from .util import browser, pathutil

FORMAT = "%(message)s"
logging.basicConfig(level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler(markup=True, show_path=False)])

app = typer.Typer()

app.add_typer(app_safemode, name="safe-mode")
app.add_typer(app_job, name="job")
app.add_typer(app_license, name="license")


def main():
    """Reads config and passes it to app"""
    config_locations = []
    home_cfg = pathlib.Path().home() / pathlib.Path(".pluprc")
    if home_cfg.exists():
        config_locations.append(home_cfg)
    try:
        project_root = pathutil.find_maven_project_root()
        project_cfg = project_root / ".pluprc"
        if project_cfg.exists():
            config_locations.append(project_cfg)
    except FileNotFoundError:
        pass
    pwd_cfg = pathlib.Path(".") / ".pluprc"
    if pwd_cfg.exists():
        config_locations.append(pwd_cfg)

    settings = {}

    for config_location in config_locations:
        with open(config_location) as stream:
            try:
                settings.update(yaml.safe_load(stream))
            except yaml.YAMLError:
                logging.warning("Looks like your configuration file is not yaml, the file will be ignored")
            except Exception as e:
                logging.warning("Config %s failed to read and will be ignored. %s", config_location, e)

    cmd: DefaultGroup = typer.main.get_command(app)
    cmd.default_if_no_args = True
    cmd.default_cmd_name = "install"
    cmd.context_settings = {"default_map": settings}
    cmd()


def version_callback(value: bool):
    if value:
        print(f"You're using {__version__}")
        raise typer.Exit()


def furl_callback(value: str) -> furl.furl:
    if value is None:
        return None
    try:
        _url = furl.furl(value)
        if not (furl.is_valid_host(_url.host) and furl.is_valid_port(_url.port) and furl.is_valid_scheme(_url.scheme)):
            raise ValueError()
    except Exception:
        raise typer.BadParameter('Make sure to provide an valid url (e.G. "https://your.confluence.net:8090")')
    return _url


@app.callback(cls=DefaultGroup)
def root(
    ctx: typer.Context,
    version: typing.Optional[bool] = typer.Option(False, "--version", callback=version_callback, is_eager=True,),
    base_url: str = typer.Option(
        "http://localhost:8090",
        help="Set the base-url of your instance. This flag will overwrite scheme, host, path and port, if those are set in"
        "this string.",
        callback=furl_callback,
        envvar="PLUP_BASEURL",
    ),
    user: str = typer.Option("admin", help="Set the username of the user you want to use", envvar="PLUP_USER",),
    password: str = typer.Option("admin", help="Set the password of the user you want to use", envvar="PLUP_PASSWORD",),
    port: typing.Optional[int] = typer.Option(None),
    ask_for_password: typing.Optional[bool] = typer.Option(False, help="Asks user for password interactively"),
    logo: bool = typer.Option(True, help="Print logo (deprecated)"),
):
    """A simple command line plugin uploader/installer/manager for atlassian product server
    instances (Confluence/Jira) written in python(3).
    """
    if ask_for_password:
        password = typer.prompt("Password: ", hide_input=True)
    burl: furl.furl = _base_url_from_args(base_url, user, password, port)
    ctx.obj = {"base_url": burl}


def _base_url_from_args(base_url: str, user: str, password: str, port: typing.Optional[int]) -> furl.furl:
    """creates furl instance from defaults, config(via defaults) and args"""
    base_url.username = user
    base_url.password = password
    if port is not None:
        base_url.port = port
    return base_url


@app.command("list")
def list_all(
    ctx: typer.Context,
    print_all: bool = typer.Option(False, help="prints all plugins instead of only user installed plugins"),
    web: bool = typer.Option(False, help="open upm in web browser after listing all plugins"),
):
    """ Prints out basic plugin informations of all plugins"""
    try:
        upm = UpmApi(ctx.obj.get("base_url"))
        all_plugins = upm.get_all_plugins(not print_all)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    table = Table()
    table.add_column("")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Plugin Key", no_wrap=True)
    for plugin in all_plugins:
        if plugin.enabled:
            status = "[green]✓[reset]"
        else:
            status = "[yellow]![reset]"
        table.add_row(status, plugin.name, plugin.version, plugin.key)
    console = Console()
    console.print(table)
    if web:
        browser.open_web_upm(ctx.obj.get("base_url"))


@app.command("info")
def plugin_info(
    ctx: typer.Context,
    plugin: str = typer.Argument(None, help="the plugin key"),
    show_modules: bool = typer.Option(False, help="show modules of plugin as well"),
    web: bool = typer.Option(False, help="open upm in web browser after showing info"),
):
    """prints information of the plugin specified by the plugin key"""
    if plugin is None:
        try:
            plugin = pathutil.get_plugin_key_from_pom()
        except FileNotFoundError:
            logging.error("Could not find the plugin you want to get the info of. Are you in a maven directory?")
            sys.exit(1)
        except pathutil.PluginKeyNotFoundError:
            logging.error("Could not find the plugin you want to get the info of. Is the plugin key set in the pom.xml?")
            sys.exit(1)
    try:
        upm = UpmApi(ctx.obj.get("base_url"))
        info = upm.get_plugin(plugin)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)

    info.print_table(show_modules)

    if web:
        browser.open_web_upm(ctx.obj.get("base_url"))


@app.command("enable")
def enable_plugin(
    ctx: typer.Context,
    plugin: str = typer.Argument(None, help="the plugin key"),
    web: bool = typer.Option(False, help="open upm in web browser after enabling plugin"),
):
    """ Enables the specified plugin """
    if plugin is None:
        try:
            plugin = pathutil.get_plugin_key_from_pom()
        except FileNotFoundError:
            logging.error("Could not find the plugin you want to get the info of. Are you in a maven directory?")
            sys.exit(1)
        except pathutil.PluginKeyNotFoundError:
            logging.error("Could not find the plugin you want to get the info of. Is the plugin key set in the pom.xml?")
            sys.exit(1)
    try:
        upm = UpmApi(ctx.obj.get("base_url"))
        response = upm.enable_disable_plugin(plugin, True)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    response.print_table(False)
    if web:
        browser.open_web_upm(ctx.obj.get("base_url"))


@app.command("disable")
def disable_plugin(
    ctx: typer.Context,
    plugin: str = typer.Argument(None, help="the plugin key"),
    web: bool = typer.Option(False, help="open upm in web browser after disabling plugin"),
):
    """ Disables the specified plugin """
    if plugin is None:
        try:
            plugin = pathutil.get_plugin_key_from_pom()
        except FileNotFoundError:
            logging.error("Could not find the plugin you want to get the info of. Are you in a maven directory?")
            sys.exit(1)
        except pathutil.PluginKeyNotFoundError:
            logging.error("Could not find the plugin you want to get the info of. Is the plugin key set in the pom.xml?")
            sys.exit(1)
    try:
        upm = UpmApi(ctx.obj.get("base_url"))
        response = upm.enable_disable_plugin(plugin, False)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    response.print_table(False)
    if web:
        browser.open_web_upm(ctx.obj.get("base_url"))


@app.command("uninstall")
def uninstall_plugin(
    ctx: typer.Context,
    plugin: str = typer.Argument(None, help="the plugin key"),
    web: bool = typer.Option(False, help="open upm in web browser after uninstalling plugin"),
):
    """Uninstalls a plugin"""
    if plugin is None:
        try:
            plugin = pathutil.get_plugin_key_from_pom()
        except FileNotFoundError:
            logging.error("Could not find the plugin you want to get the info of. Are you in a maven directory?")
            sys.exit(1)
        except pathutil.PluginKeyNotFoundError:
            logging.error("Could not find the plugin you want to get the info of. Is the plugin key set in the pom.xml?")
            sys.exit(1)
    try:
        upm = UpmApi(ctx.obj.get("base_url"))
        status = upm.uninstall_plugin(plugin)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    if status:
        logging.info("Plugin successfully uninstalled")
    else:
        logging.error("An error occurred. The plugin could not be uninstalled.")
    if web:
        browser.open_web_upm(ctx.obj.get("base_url"))


@app.command("install")
def install(
    ctx: typer.Context,
    cloud: bool = typer.Option(False, "--cloud"),
    file: typing.Optional[pathlib.Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="pluploader tries find an plugin in the current directory. If you want to specify the location of the plugin you "
        "want to upload, use -f /path/to/jar",
    ),
    plugin_uri: typing.Optional[str] = typer.Option(
        None,
        "--plugin-uri",
        "-u",
        callback=furl_callback,
        help="CLOUD ONLY: The uri/url of to the app descriptor, for example "
        "https://placeholder.ngrok.com/atlassian-connect.json",
    ),
    mpac_id: typing.Optional[str] = typer.Option(
        None,
        "--mpac-id",
        help="""When mpac-id is specified, pluploader tries to download the specified plugin from the marketplace.\n
The marketplace id can be found in the url: 1213057 in https://marketplace.atlassian.com/apps/1213057\n
To specify the version, use the == syntax: 1213057==3.10.1 will download 3.10.1\n
Warning: mpac-id is considered unstable; consider using --mpac-key
""",
    ),
    mpac_key: typing.Optional[str] = typer.Option(
        None,
        "--mpac-key",
        help="""When mpac-key is specified, pluploader tries to download the specified plugin from the marketplace.
The mpac-key is the app key.\n
To specify the version, use the == syntax: 1213057==3.10.1 will download 3.10.1""",
    ),
    interactive: typing.Optional[bool] = typer.Option(False, "--interactive", "-i", help="confirm the upload of the app",),
    reinstall: typing.Optional[bool] = typer.Option(
        False, "--reinstall", help="Plugin will be uninstalled before it will be installed"
    ),
    web: bool = typer.Option(False, help="open upm in web browser after installing plugin"),
):
    """installs the plugin of the current maven project or a specified one; you can also omit install"""
    base_url: furl.furl = ctx.obj.get("base_url")
    if cloud:
        if plugin_uri is None:
            raise typer.BadParameter("--plugin-uri is required when --cloud is set")
        install_cloud(base_url, plugin_uri)
    else:
        install_server(base_url, file, mpac_id, mpac_key, interactive, reinstall)
    if web:
        browser.open_web_upm(ctx.obj.get("base_url"))


def install_cloud(base_url: furl.furl, plugin_uri: furl.furl):
    try:
        cloud = UpmCloudApi(base_url)
        token = cloud.get_token()
    except requests.exceptions.RequestException:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except KeyError:
        logging.error("UPM Token couldn't be retrieved; are your credentials correct?")
        sys.exit(1)

    displayed_base_url = base_url.copy().remove(username=True, password=True)
    logging.info(f"{plugin_uri} will be uploaded to {displayed_base_url}")

    try:
        response = cloud.install_plugin(plugin_uri, token)
        with Progress(
            "[progress.description]{task.description}",
            "[[blue]{task.percentage:>3.0f}%[reset]]",
            BarColumn(bar_width=None, complete_style="blue", finished_style="blue"),
        ) as pbar:
            task = pbar.add_task("[blue]Installing...", total=100)
            percentage = 0
            pbar.update(task, completed=percentage)
            while percentage != 100:
                percentage, plugin = cloud.install_plugin_get_current_progress(response)
                pbar.update(task, completed=percentage)
                if percentage != 100:
                    time.sleep(0.1)
    except requests.exceptions.RequestException as e:
        logging.error("An error occured while uploading plugin %s", e)
        sys.exit(1)
    except Exception as e:
        logging.error("An error occured while uploading plugin %s", e)
        sys.exit(1)

    if plugin and plugin.enabled:
        status = "[green]enabled[reset]!"
    else:
        status = "[red]disabled[reset]!"
    logging.info(f"plugin installed and {status}")


def install_server(
    base_url: furl.furl,
    file: typing.Optional[pathlib.Path],
    mpac_id: typing.Optional[str],
    mpac_key: typing.Optional[str],
    interactive: typing.Optional[bool],
    reinstall: typing.Optional[bool],
):
    try:
        if file is not None:
            plugin_path = file
        elif mpac_id is not None:
            id, version = download.split_name_and_version(mpac_id)
            logging.info("Downloading app %s (%s)...", id, version)
            plugin_path = download.download_app_by_marketplace_id(id, version)
            logging.info("Successfully downloaded app to %s", plugin_path)
        elif mpac_key is not None:
            key, version = download.split_name_and_version(mpac_key)
            logging.info("Downloading app %s (%s)...", key, version)
            plugin_path = download.download_app_by_app_key(key, version)
            logging.info("Successfully downloaded app to %s", plugin_path)
        else:
            try:
                plugin_path = pathutil.get_jar_path_from_pom()
            except FileNotFoundError:
                logging.error("Could not find the plugin you want to install. Are you in a maven directory?")
                sys.exit(1)
    except (MpacAppNotFoundError, MpacAppVersionNotFoundError) as e:
        logging.error("Could not find the plugin or plugin version %s", e)
        sys.exit(1)
    except Exception as e:
        logging.error("An error occured while downloading an app from the marketplace %s", e)
        sys.exit(1)

    if interactive:
        confirm = input("Do you really want to upload and install the plugin? (y/N) ")
        if confirm.lower() != "y":
            sys.exit()

    upm = UpmApi(base_url)
    if plugin_path.suffix == ".obr":
        plugin_info = jar.get_plugin_info_from_obr_path(plugin_path)
    else:
        plugin_info = jar.get_plugin_info_from_jar_path(plugin_path)
    if reinstall:
        try:
            try:
                status = upm.uninstall_plugin(plugin_info.key)
            except requests.exceptions.ConnectionError:
                logging.error("Could not connect to host - check your base-url")
                sys.exit(1)
            except Exception as exc:
                logging.error("An error occured - check your credentials")
                logging.error("%s", exc)
                sys.exit(1)
            if status:
                logging.info("Plugin successfully uninstalled")
            else:
                logging.error("An error occurred. The plugin could not be uninstalled.")
        except (FileNotFoundError, zipfile.BadZipFile, KeyError, pathutil.PluginKeyNotFoundError):
            logging.error("Could not get the plugin key of the supplied jar - are you sure you want to upload a plugin, mate?")
    else:
        # WORKAROUND: replace -SNAPSHOT with .dev, to follow python versioning scheme
        # TODO: find a new library that can parse -SNAPSHOT correctly
        version_to_install = version_parse(plugin_info.version.replace("-SNAPSHOT", ".dev"))
        try:
            # WORKAROUND: replace -SNAPSHOT with .dev, to follow python versioning scheme
            # TODO: find a new library that can parse -SNAPSHOT correctly
            version_installed = version_parse(upm.get_plugin(plugin_info.key).version.replace("-SNAPSHOT", ".dev"))
            if version_installed > version_to_install:
                logging.warning(
                    f"Looks like you are trying to install a .jar with a lower version ({version_to_install}) than already "
                    f"installed ({version_installed}).\n"
                    "This will most likely fail. Use the --reinstall option to uninstall the plugin first."
                )
        except json.decoder.JSONDecodeError:
            # If we can't get the current plugin, this means that the plugin is installed for the first time.
            # In this case, we can just ignore the error and perceed
            pass

    displayed_base_url = base_url.copy().remove(username=True, password=True)
    logging.info(f"{pathlib.Path(plugin_path).name} will be uploaded to {displayed_base_url}")

    try:
        token = upm.get_token()
    except requests.exceptions.RequestException:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except KeyError:
        logging.error("UPM Token couldn't be retrieved; are your credentials correct?")
        sys.exit(1)

    try:
        with open(plugin_path, "rb") as plugin_file:
            files = {"plugin": plugin_file}
            with Progress(
                "[progress.description]{task.description}",
                "[[blue]{task.percentage:>3.0f}%[reset]]",
                BarColumn(bar_width=None, complete_style="blue", finished_style="blue"),
            ) as pbar:
                task = pbar.add_task("[blue]Installing...", total=100)
                progress, previous_request = upm.upload_plugin(files, token)
                while progress != 100:
                    progress, previous_request = upm.get_current_progress(previous_request)
                    pbar.update(task, completed=progress)
                    time.sleep(0.1)
    except requests.exceptions.RequestException:
        logging.error("An error occured while uploading plugin")
        sys.exit(1)
    except FileNotFoundError:
        logging.error("Could not find the plugin you want to install.")
        sys.exit(1)
    finally:
        for file in files.values():
            file.close()

    plugin_data = PluginDto.decode(previous_request)

    if plugin_data.enabled:
        status = "[green]enabled[reset]!"
    else:
        status = (
            "[red]disabled[reset]! \n"
            "You should check the logs of your Atlassian host to find out why your plugin was disabled."
        )
    all_nr, enabled, disabled = upm.module_status(previous_request)
    logging.info(
        f"plugin {plugin_data.name} ({plugin_data.key}, v{plugin_data.version}) uploaded"
        f" and {status} ({enabled} of {all_nr} modules enabled)"
    )
    if len(disabled) != 0 and len(disabled) != all_nr:
        for module in disabled:
            logging.info(f"   - {module.key} is disabled")
    elif len(disabled) == all_nr:
        logging.error(
            "Your plugin was installed successfully but all modules are disabled. This is often caused by problems such as"
            " importing services that are not properly defined in your atlassian-plugin.xml."
        )
        logging.error("Check the logs of your Atlassian host to find out more.")


@app.command("api")
def api(
    ctx: typer.Context,
    endpoint: str = typer.Argument(..., help="path of the endpoint you want to use"),
    body: str = typer.Argument("", help="body of the request you want to send"),
    method: str = typer.Option("GET", "-X", help="choose http method",),
    header: typing.List[str] = typer.Option([], "-H", help="Provide additional headers",),
):
    """Make an authenticated request to the atlassian product server"""
    base_url: furl.furl = ctx.obj.get("base_url")

    session = requests.Session()
    endpoint_f = furl.furl(endpoint)
    url = base_url.copy().add(path=endpoint_f.path).set(query=str(endpoint_f.query))
    req = requests.Request(method=method, url=url)
    req.headers = {
        **req.headers,
        **{x.split(":", 1)[0].strip(): x.split(":", 1)[1].strip() for x in header},
    }
    if method.lower() == "post" or method.lower() == "put":
        req.data = body

    prepared = req.prepare()
    response = session.send(prepared)
    print(response.text)


@app.command("rpc",)
def rpc(
    ctx: typer.Context,
    method: str = typer.Argument(..., help="method you want to execute on the remote confluence"),
    arguments: typing.List[str] = typer.Argument(
        ..., help="all arguments you want to pass to the method with. For classes/objects, provide a json string.",
    ),
):
    """
    this command allows interaction with the (deprecated, but  still functional)
    confluence rpc api by providing the method name and it's required arguments.
    You do not need to care about the rpc-authentication, as this command
    takes care of it. Therefore, you can also obmit the first parameter (String token)
    required for many commands.

    EXAMPLES:

        pluploader rpc addUser '{"name":"charlie", "fullname": "charlie", "email":"charlie@charlie"}' charlie

    You can find all available methods that the rpc-api offers in this documentation:

    https://developer.atlassian.com/server/confluence/remote-confluence-methods/
    """

    def try_to_json(input):
        return_val = input
        try:
            return_val = json.loads(input)
        except Exception:
            pass
        return return_val

    base_url: furl.furl = ctx.obj.get("base_url")
    with rpcclient.ServerProxy(str(base_url.add(path="rpc/xmlrpc"))) as proxy:
        try:
            token = proxy.confluence2.login(base_url.username, base_url.password)
            method = getattr(proxy.confluence2, method)
            response = method(token, *map(try_to_json, arguments))
            print(json.dumps(response, default=str))
        except RpcProtocolError as e:
            logging.error("An error occured: %s", e)
            if e.errcode == 403:
                logging.error("Do you have xml-rpc enabled?")
        except Exception as e:
            logging.error("An error occured: %s", e)


if __name__ == "__main__":
    main()
