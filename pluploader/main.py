""" pluploader executable
"""
import logging
import pathlib
import shutil
import sys
import time
import typing

import coloredlogs
import furl
import requests
import typer
import yaml
from click_default_group import DefaultGroup
from colorama import Fore
from tqdm import tqdm
import zipfile

from . import __version__, jobs, pathutil
from . import atlas_jar_util as jar
from . import upmapi as upm

app = typer.Typer()
app_safemode = typer.Typer()
app_job = typer.Typer()

app.add_typer(app_safemode, name="safe-mode")
app.add_typer(app_job, name="job")

LOGO = f"""
{Fore.YELLOW} ))))          {Fore.RED}           ((((
{Fore.YELLOW} )))))))       {Fore.RED}        (((((((
{Fore.YELLOW}  ))))))))     {Fore.RED}      ((((((((
{Fore.YELLOW}  ))))))))))   {Fore.RED}    ((((((((((
{Fore.YELLOW}   ))))))))))) {Fore.RED}  (((((((((((
{Fore.YELLOW}    ))))))))))){Fore.GREEN}|{Fore.RED}(((((((((((
{Fore.YELLOW}     ))))))))){Fore.GREEN}|||{Fore.RED}(((((((((
{Fore.YELLOW}      ))))))){Fore.GREEN}|||||{Fore.RED}(((((((
{Fore.YELLOW}        )))){Fore.GREEN}|||||||{Fore.RED}((((
{Fore.YELLOW}          )){Fore.GREEN}|||||||{Fore.RED}((
{Fore.YELLOW}            {Fore.RED}/{Fore.GREEN}|||||{Fore.YELLOW}\\
{Fore.RESET}"""

coloredlogs.install(level="DEBUG")
coloredlogs.install(fmt="%(asctime)s %(levelname)s %(message)s")


def main():
    """ Reads config and passes it to app
    """
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
    settings = {}

    for config_location in config_locations:
        with open(config_location) as stream:
            try:
                settings.update(yaml.safe_load(stream))
            except yaml.YAMLError:
                logging.warning("Looks like your configuration file is not yaml, the file will be ignored")

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
    try:
        _url = furl.furl(value)
        if not (furl.is_valid_host(_url.host) and furl.is_valid_port(_url.port) and furl.is_valid_scheme(_url.scheme)):
            raise ValueError
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
    ),
    user: str = typer.Option("admin", help="Set the username of the user you want to use",),
    password: str = typer.Option("admin", help="Set the password of the user you want to use",),
    port: typing.Optional[int] = typer.Option(None),
    ask_for_password: typing.Optional[bool] = typer.Option(False, help="Asks user for password interactively"),
    logo: bool = typer.Option(True, help="Print lively apps logo"),
):
    """ A simple command line plugin uploader/installer/manager for atlassian product server
    instances (Confluence/Jira) written in python(3).
    """
    if logo:
        print(LOGO)
    if ask_for_password:
        password = typer.prompt("Password: ", hide_input=True)
    burl: furl.furl = _base_url_from_args(base_url, user, password, port)
    ctx.obj = {"base_url": burl}


def _base_url_from_args(base_url: str, user: str, password: str, port: typing.Optional[int]) -> furl.furl:
    """creates furl instance from defaults, config(via defaults) and args
    """
    base_url.username = user
    base_url.password = password
    if port is not None:
        base_url.port = port
    return base_url


@app.command("list")
def list_all(
    ctx: typer.Context, print_all: bool = typer.Option(False, help="prints all plugins instead of only user installed plugins")
):
    """ Prints out basic plugin informations of all plugins"""
    try:
        all_plugins = upm.get_all_plugins(ctx.obj.get("base_url"), not print_all)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    print(f"  {'Name':25} {'Version':13} {'Plugin Key':50}")
    for plugin in all_plugins:
        if plugin.enabled:
            status = f"{Fore.GREEN}✓{Fore.RESET}"
        else:
            status = f"{Fore.YELLOW}!{Fore.RESET}"

        plugin_infos = f"{status} {plugin.name[:25]:25}" + f" {str(plugin.version)[:13]:13} ({plugin.key})"
        print(plugin_infos)


@app.command("info")
def plugin_info(
    ctx: typer.Context,
    plugin: str = typer.Argument(None, help="the plugin key"),
    show_modules: bool = typer.Option(False, help="show modules of plugin as well"),
):
    """ prints information of the plugin specified by the plugin key
    """
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
        info = upm.get_plugin(ctx.obj.get("base_url"), plugin)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    info.print_table(show_modules)


@app.command("enable")
def enable_plugin(
    ctx: typer.Context, plugin: str = typer.Argument(None, help="the plugin key"),
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
        response = upm.enable_disable_plugin(ctx.obj.get("base_url"), plugin, True)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    response.print_table(False)


@app.command("disable")
def disable_plugin(
    ctx: typer.Context, plugin: str = typer.Argument(None, help="the plugin key"),
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
        response = upm.enable_disable_plugin(ctx.obj.get("base_url"), plugin, False)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    response.print_table(False)


@app.command("uninstall")
def uninstall_plugin(
    ctx: typer.Context, plugin: str = typer.Argument(None, help="the plugin key"),
):
    """ Uninstalls a plugin
    """
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
        status = upm.uninstall_plugin(ctx.obj.get("base_url"), plugin)
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


@app.command("install")
def install(
    ctx: typer.Context,
    file: typing.Optional[pathlib.Path] = typer.Option(None, "--file", "-f", help=""),
    interactive: typing.Optional[bool] = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Pluploader tries find an plugin in the current directory. If you want to specify the location of the plugin "
        "you want to upload, use -f /path/to/jar",
    ),
    reinstall: typing.Optional[bool] = typer.Option(
        False, "--reinstall", help="Plugin will be uninstalled before it will be installed"
    ),
):
    """installs the plugin of the current maven project or a specified one; you can also omit install
    """
    base_url: furl.furl = ctx.obj.get("base_url")
    if file is None:
        try:
            plugin_path = pathutil.get_jar_path_from_pom()
        except FileNotFoundError:
            logging.error("Could not find the plugin you want to install. Are you in a maven directory?")
            sys.exit(1)
    else:
        plugin_path = file

    displayed_base_url = base_url.copy().remove(username=True, password=True)

    if interactive:
        confirm = input("Do you really want to upload and install the plugin? (y/N) ")
        if confirm.lower() != "y":
            sys.exit()

    if reinstall:
        try:
            plugin_key = jar.get_plugin_key_from_jar_path(plugin_path)
            try:
                status = upm.uninstall_plugin(base_url, plugin_key)
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

    logging.info(f"{pathlib.Path(plugin_path).name} will be uploaded to {displayed_base_url}")

    try:
        token = upm.get_token(base_url)
    except requests.exceptions.RequestException:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except KeyError:
        logging.error("UPM Token couldn't be retrieved; are your credentials correct?")
        sys.exit(1)

    try:
        with open(plugin_path, "rb") as plugin_file:
            files = {"plugin": plugin_file}
            with TqdmUpTo(total=100) as pbar:
                pbar.update_to(0)
                progress, previous_request = upm.upload_plugin(base_url, files, token)
                while progress != 100:
                    progress, previous_request = upm.get_current_progress(base_url, previous_request)
                    pbar.update_to(progress)
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

    if previous_request["enabled"]:
        status = f"{Fore.GREEN}enabled{Fore.RESET}!"
    else:
        status = (
            f"{Fore.RED}disabled{Fore.RESET}! \n"
            "You should check the logs of your Atlassian host to find out why your plugin was disabled."
        )

    all_nr, enabled, disabled = upm.module_status(previous_request)
    logging.info("plugin uploaded and " + status + f" ({enabled} of {all_nr} modules enabled)")
    if len(disabled) != 0 and len(disabled) != all_nr:
        for module in disabled:
            logging.info(f"   - {module.key} is disabled")
    elif len(disabled) == all_nr:
        logging.error(
            "Your plugin was installed successfully but all modules are disabled. This is often caused by problems such as"
            " importing services that are not properly defined in your atlassian-plugin.xml."
        )
        logging.error("Check the logs of your Atlassian host to find out more.")


@app_safemode.callback()
def safemode(ctx: typer.Context):
    """ Controls the upm safemode
    """


@app_safemode.command("status")
def safemode_status(ctx: typer.Context):
    """ prints out the safemode status """
    try:
        safemode_st = (
            f"{Fore.YELLOW}enabled{Fore.RESET}"
            if upm.get_safemode(ctx.obj.get("base_url"))
            else f"{Fore.GREEN}disabled{Fore.RESET}"
        )
        logging.info("Safe-mode is currently %s", safemode_st)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as e:
        logging.error("An error occured - check your credentials")
        logging.error(f"{e}")
        sys.exit(1)


@app_safemode.command("enable")
def safemode_enable(ctx: typer.Context):
    try:
        success = upm.enable_disable_safemode(ctx.obj.get("base_url"), True)
        if success:
            logging.info(f"Safe-mode is now {Fore.GREEN}enabled{Fore.RESET}")
        else:
            logging.error("Could not enable safe-mode - is safe-mode already enabled?")
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)


@app_safemode.command("disable")
def safemode_disable(ctx: typer.Context, keep_state: bool = typer.Option(False)):
    try:
        success = upm.enable_disable_safemode(ctx.obj.get("base_url"), False, keep_state)
        if success:
            logging.info(
                f"Safe-mode is now {Fore.GREEN}disabled{Fore.RESET}, all plugins"
                f"{'got restored' if not keep_state else 'stayed disabled'}."
            )
        else:
            logging.error("Could not disable safe-mode - is safe-mode already disabled?")
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)


@app_job.command("list")
def job_list(
    ctx: typer.Context,
    hide_default: typing.Optional[bool] = typer.Option(False),
    print_all_infos: typing.Optional[bool] = typer.Option(False),
):
    """ Confluence only, list all jobs available
    """
    try:
        logging.info("Getting jobs... This can take some time - please wait!")
        _job_list, token, cookies = jobs.list_jobs(ctx.obj.get("base_url"))

        columns, _ = shutil.get_terminal_size(fallback=(80, 24))

        width = int((columns - 17) / 4)
        print(
            f"{Fore.LIGHTBLACK_EX}{'idx':3} {'name':{width}} {'group':{width*2}} {'id':{width}} {'STS':3} {'RUNBL':5}{Fore.RESET}"
        )
        if print_all_infos:
            print(
                f"{Fore.LIGHTBLACK_EX}        {'last execution':{width}} {'next execution':{width}} {'avg duration':7}{Fore.RESET}"
            )
        print(f"{Fore.LIGHTBLACK_EX}{'='*columns}{Fore.RESET}")
        for idx, job in enumerate(_job_list):
            if hide_default and job.group == "DEFAULT":
                continue
            status_emoji = "🔄" if job.status == "Scheduled" else "❌"
            if job.is_runnable:
                runnable_emoji = f"{Fore.GREEN}✓{Fore.RESET}"
            else:
                runnable_emoji = f"{Fore.RED}!{Fore.RESET}"
            print(
                f"{Fore.YELLOW}{idx:3}{Fore.RESET} {job.name:{width}.{width}} {job.group:{width*2}.{width*2}}",
                f"{job.id:{width}.{width}} {status_emoji:2.6} {runnable_emoji}",
            )
            if print_all_infos:
                print(
                    f"        {job.last_execution:{width}.{width}} {job.next_execution:{width}.{width}}",
                    f"{job.avg_duration:{width}.{width}}",
                )
                print(f"{Fore.LIGHTBLACK_EX}{'-'*columns}{Fore.RESET}")
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)


def _select_job(
    _job_list: typing.List[jobs.Job],
    idx: typing.Optional[int] = None,
    id: typing.Optional[str] = None,
    group: typing.Optional[str] = None,
) -> jobs.Job:
    selected_job = None

    if id is not None:
        possible_jobs = [x for x in _job_list if id in x.id]
        if len(possible_jobs) > 1 and group is not None:
            possible_jobs = [x for x in possible_jobs if group in x.group]

        if len(possible_jobs) == 1:
            selected_job = possible_jobs[0]
        elif len(possible_jobs) > 0:
            # TODO: ADD SELECTION HERE
            pass
    elif idx is not None:
        selected_job = _job_list[idx] if idx < len(_job_list) else None
    else:
        columns, _ = shutil.get_terminal_size(fallback=(80, 24))

        width = int((columns - 15) / 4)
        print(f"{Fore.LIGHTBLACK_EX}{'idx':3} {'name':{width}} {'group':{width*2}} {'id':{width}} runnable")
        for idx, job in enumerate(_job_list):
            if job.is_runnable:
                runnable_emoji = f"{Fore.GREEN}✓{Fore.RESET}"
            else:
                runnable_emoji = f"{Fore.RED}!{Fore.RESET}"
            print(
                f"{Fore.YELLOW}{idx:3}{Fore.RESET} {job.name:{width}.{width}} {job.group:{width*2}.{width*2}}",
                f"{job.id:{width}.{width}} {runnable_emoji}",
            )

        while True:
            _idx = typer.prompt("Select a job index (idx)")
            if int(_idx) >= 0 and int(_idx) < len(_job_list):
                idx = int(_idx)
                selected_job = _job_list[idx]
                break

    if selected_job is None:
        logging.error("job could not be found")
        typer.Exit(1)

    return selected_job


@app_job.command("run")
def job_run(
    ctx: typer.Context,
    idx: typing.Optional[int] = typer.Option(None),
    id: typing.Optional[str] = typer.Option(None),
    group: typing.Optional[str] = typer.Option(None),
):
    """ Confluence only, runs a specified job
    """
    try:
        logging.info("Getting jobs... This can take some time - please wait!")
        base_url = ctx.obj.get("base_url")
        _job_list, token, cookies = jobs.list_jobs(base_url)

        selected_job = _select_job(_job_list, idx, id, group)

        logging.info(f"Job {selected_job.name} ({selected_job.id}) selected - Trying to run the job now")

        success = jobs.run_job(base_url, selected_job, token, cookies)
        if success:
            logging.info("Started job successfully!")
        else:
            logging.error("Couldn't start job!")

    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)


@app_job.command("info")
def job_info(
    ctx: typer.Context,
    idx: typing.Optional[int] = typer.Option(None),
    id: typing.Optional[str] = typer.Option(None),
    group: typing.Optional[str] = typer.Option(None),
):
    try:
        logging.info("Getting jobs... This can take some time - please wait!")
        base_url = ctx.obj.get("base_url")
        _job_list, token, cookies = jobs.list_jobs(base_url)

        selected_job = _select_job(_job_list, idx, id, group)
        for key, value in selected_job.__dict__.items():
            print(f"{(key.replace('_', ' ') + ':'):25.25} {value}")
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)


@app_job.command("disable")
def job_disable(
    ctx: typer.Context,
    idx: typing.Optional[int] = typer.Option(None),
    id: typing.Optional[str] = typer.Option(None),
    group: typing.Optional[str] = typer.Option(None),
):
    """ Confluence only, disable a specified job
    """
    try:
        logging.info("Getting jobs... This can take some time - please wait!")
        base_url = ctx.obj.get("base_url")
        _job_list, token, cookies = jobs.list_jobs(base_url)

        selected_job = _select_job(_job_list, idx, id, group)

        logging.info(f"Job {selected_job.name} ({selected_job.id}) selected - Trying to disable the job now")

        success = jobs.disable_job(base_url, selected_job, token, cookies)
        if success:
            logging.info("Disabled job successfully!")
        else:
            logging.error("Couldn't disable job!")
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)


@app_job.command("enable")
def job_enable(
    ctx: typer.Context,
    idx: typing.Optional[int] = typer.Option(None),
    id: typing.Optional[str] = typer.Option(None),
    group: typing.Optional[str] = typer.Option(None),
):
    """ Confluence only, enable a specified job
    """
    try:
        logging.info("Getting jobs... This can take some time - please wait!")
        base_url = ctx.obj.get("base_url")
        _job_list, token, cookies = jobs.list_jobs(base_url)

        selected_job = _select_job(_job_list, idx, id, group)

        logging.info(f"Job {selected_job.name} ({selected_job.id}) selected - Trying to enable the job now")

        success = jobs.enable_job(base_url, selected_job, token, cookies)
        if success:
            logging.info("Enabled job successfully!")
        else:
            logging.error("Couldn't enable job!")
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)


class TqdmUpTo(tqdm):
    """Provides `update_to(n)` which uses `tqdm.update(delta_n)`."""

    def update_to(self, b=1, bsize=1, tsize=None):
        """
        b  : int, optional
            Number of blocks transferred so far [default: 1].
        bsize  : int, optional
            Size of each block (in tqdm units) [default: 1].
        tsize  : int, optional
            Total size (in tqdm units). If [default: None] remains unchanged.
        """
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)  # will also set self.n = b * bsize


if __name__ == "__main__":
    main()
