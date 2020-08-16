""" pluploader executable
"""

import getpass
import logging
import pathlib
import sys
import time

import coloredlogs
import configargparse
import requests
from colorama import Fore
from furl import furl
from tqdm import tqdm
import zipfile

import pluploader
from pluploader import pathutil
from pluploader import upmapi as upm
from pluploader import atlas_jar_util as jar

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


def main():
    """ Sets up configargparse
    """
    config_locations = ["~/.pluprc"]
    try:
        project_root = pathutil.find_maven_project_root()
        config_locations.append(project_root / ".pluprc")
    except FileNotFoundError:
        pass

    p = configargparse.ArgParser(
        default_config_files=config_locations, config_file_parser_class=configargparse.YAMLConfigFileParser,
    )
    p.add_argument(
        "--base-url",
        default="http://localhost:8090",
        help="Set the base-url of your instance. This flag will overwrite "
        "scheme, host, path and port, if those are set in this string."
        "Defaults to: http://localhost:8090",
    )
    p.add_argument(
        "--user", default="admin", help="Set the username of the user you want to use. Defaults to admin",
    )
    p.add_argument(
        "-p", "--password", default="admin", help="Set the password of the user you want to use. Defaults to admin",
    )
    p.add_argument(
        "--scheme", default="http", help="Set the HTTP-Scheme you want to use. Defaults to http. " "Options: http, https",
    )
    p.add_argument(
        "--host", default="localhost", help="Set the host you want to use; Defaults to localhost",
    )
    p.add_argument(
        "--path", default="/", help="Set the context-path you want to use. Defaults to /; " "You may want to use /confluence",
    )
    p.add_argument("--port", default="8090", help="Defaults to 8090")
    p.add_argument(
        "-f",
        "--file",
        type=lambda p: pathlib.Path(p),
        help="Pluploader tries find an plugin in the current directory. If you want to specify the location of the plugin you"
        "want to upload, use -f /path/to/jar",
    )
    p.add_argument(
        "-i",
        "--interactive",
        default=False,
        action="store_true",
        help="You will be asked if you really want to upload the plugin",
    )
    p.add_argument(
        "--reinstall", default=False, action="store_true", help="Plugin will be uninstalled before it will be installed",
    )
    p.add_argument(
        "-P", "--ask-for-password", default=False, action="store_true", help="Asks user for password interactively",
    )
    p.add_argument(
        "--no-logo", default=False, action="store_true", help="the lively apps logo will not be printed",
    )
    p.add_argument("--version", default=False, action="store_true")

    commandparser = p.add_subparsers(dest="command")

    listparser = commandparser.add_parser("list", help="list all installed plugins")
    listparser.add_argument(
        "--all",
        help="prints all plugins instead of only user installed plugins",
        action="store_true",
        default=False,
        dest="print_all",
    )

    infoparser = commandparser.add_parser("info", help="prints information of the plugin specified by the plugin key")
    infoparser.add_argument("plugin", nargs="?", default=None)
    infoparser.add_argument("--show-modules", default=False, action="store_true")

    enable_parser = commandparser.add_parser("enable", help="enables specified plugin")
    enable_parser.add_argument("plugin", nargs="?", default=None)

    disable_parser = commandparser.add_parser("disable", help="disables specified plugin")
    disable_parser.add_argument("plugin", nargs="?", default=None)

    uninstall_parser = commandparser.add_parser("uninstall", help="uninstalls specified plugin")
    uninstall_parser.add_argument("plugin", nargs="?", default=None)

    safemode_parser = commandparser.add_parser("safe-mode", help="controls safe-mode")
    safemode_subparser = safemode_parser.add_subparsers(dest="subcommand")
    safemode_subparser.add_parser("status", help="prints the current status of safe-mode")
    safemode_subparser.add_parser("enable", help="enables safe-mode")
    safemode_disable_parser = safemode_subparser.add_parser("disable", help="disables safe-mode")
    safemode_disable_parser.add_argument(
        "--keep-state",
        default=False,
        action="store_true",
        help="If keep-state is enabled, safe-mode will be disabled, but all" "plugins will stay disabled",
    )

    commandparser.add_parser(
        "install", help="installs the plugin of the current maven project or a specified one; you can also omit install",
    )

    args = p.parse_args()
    all_defaults = {key: p.get_default(key) for key in vars(args)}
    _run(args, all_defaults)


def _run(args, all_defaults):
    """ Decides which command gets executed
    """
    if not args.no_logo:
        print(LOGO)

    if args.version:
        print(pluploader.__version__)
        sys.exit(0)

    base_url: furl = _base_url_from_args(args, all_defaults)

    if args.command == "list":
        list_all(base_url, args)
    elif args.command == "enable":
        enable_plugin(base_url, args)
    elif args.command == "disable":
        disable_plugin(base_url, args)
    elif args.command == "uninstall":
        uninstall_plugin(base_url, args)
    elif args.command == "info":
        plugin_info(base_url, args)
    elif args.command == "safe-mode":
        if args.subcommand == "status" or args.subcommand is None:
            safemode_status(base_url, args)
        elif args.subcommand == "enable":
            safemode_enable(base_url, args)
        elif args.subcommand == "disable":
            safemode_disable(base_url, args)
    elif args.command == "install" or args.command is None:
        install(base_url, args)


def _base_url_from_args(args, defaults) -> furl:
    """creates furl instance from defaults, config(via defaults) and args
    """
    base_url: furl = furl(args.base_url)
    if args.scheme != defaults["scheme"]:
        base_url.scheme = args.scheme
    if args.host != defaults["host"]:
        base_url.host = args.host
    if args.port != defaults["port"]:
        base_url.port = args.port
    if args.path != defaults["path"]:
        base_url.path = args.path

    base_url.username = args.user
    base_url.password = args.password
    if args.ask_for_password:
        base_url.password = getpass.getpass()
    return base_url


def list_all(base_url, args):
    """ Prints out basic plugin informations of all plugins"""
    try:
        all_plugins = upm.get_all_plugins(base_url, not args.print_all)
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


def plugin_info(base_url, args):
    """ Prints out all available information about a plugin """
    plugin = args.plugin
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
        info = upm.get_plugin(base_url, plugin)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    info.print_table(args.show_modules)


def enable_plugin(base_url, args):
    """ Enables the specified plugin """
    plugin = args.plugin
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
        response = upm.enable_disable_plugin(base_url, plugin, True)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    response.print_table(False)


def disable_plugin(base_url, args):
    """ Disables the specified plugin """
    plugin = args.plugin
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
        response = upm.enable_disable_plugin(base_url, plugin, False)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    response.print_table(False)


def uninstall_plugin(base_url, args):
    """ Uninstalls a plugin; If no plugin is given by the url, try to uninstall
    the plugin of the current dir """
    plugin = args.plugin
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
        status = upm.uninstall_plugin(base_url, plugin)
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


def install(base_url, args):
    """ Actual code of the pluploader
    """
    # TODO: Refactor this to somehow use "with"
    if args.file is None:
        plugin_path = pathutil.get_jar_path_from_pom()
    else:
        plugin_path = args.file

    logging.info(f"{plugin_path.name} will be uploaded to {base_url.host}:{base_url.port}")
    if args.reinstall:
        logging.info("--reinstall is enabled. The plugin will be uninstalled first.")
    if args.interactive:
        confirm = input("Do you really want to upload and install the plugin? (y/N) ")
        if confirm.lower() != "y":
            sys.exit()

    if args.reinstall:
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
        except (FileNotFoundError, zipfile.BadZipFile, KeyError, pluploader.pathutil.PluginKeyNotFoundError):
            logging.error("Could not get the plugin key of the supplied jar - are you sure you want to upload a plugin, mate?")

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


def safemode_status(base_url, args):
    """ prints out the safemode status """
    try:
        safemode_st = (
            f"{Fore.YELLOW}enabled{Fore.RESET}" if upm.get_safemode(base_url) else f"{Fore.GREEN}disabled{Fore.RESET}"
        )
        logging.info("Safe-mode is currently %s", safemode_st)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as e:
        logging.error("An error occured - check your credentials")
        logging.error(f"{e}")
        sys.exit(1)


def safemode_enable(base_url, args):
    try:
        success = upm.enable_disable_safemode(base_url, True)
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


def safemode_disable(base_url, args):
    try:
        success = upm.enable_disable_safemode(base_url, False, args.keep_state)
        if success:
            logging.info(
                f"Safe-mode is now {Fore.GREEN}disabled{Fore.RESET}, all plugins"
                f"{'got restored' if not args.keep_state else 'stayed disabled'}."
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


if __name__ == "__main__":
    main()
