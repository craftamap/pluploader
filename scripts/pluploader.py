""" pluploader executable
"""

import time
import sys
import os.path
import configargparse
import logging
from tqdm import tqdm
from colorama import Fore
import coloredlogs

from pluploader import pathutil
from pluploader import upmapi as upm

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

coloredlogs.install(level='DEBUG')
coloredlogs.install(fmt='%(asctime)s %(levelname)s %(message)s')

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
    """ Main method
    """
    project_root = pathutil.find_maven_project_root(".")
    config_locations = ["~/.pluprc"]

    if project_root is not False:
        config_locations.append(os.path.join(project_root, ".pluprc"))
    p = configargparse.ArgParser(
        default_config_files=config_locations,
        config_file_parser_class=configargparse.YAMLConfigFileParser)
    p.add("--host", default="localhost")
    p.add("--scheme", default="http")
    p.add("--user", required=True)
    p.add("--password", required=True)
    p.add("--port", default="8090")
    p.add("-f", "--file", type=configargparse.FileType("rb"))
    p.add("-i", "--interactive", default=False, action='store_true')
    p.add("--no-logo",default=False, action="store_true")

    commandparser = p.add_subparsers(dest="command")

    listparser = commandparser.add_parser("list")
    listparser.add_argument("--all",
                            help="Print all plugins instead of only user installed plugins",
                            action="store_true",
                            default=False,
                            dest="print_all"
                            )

    infoparser = commandparser.add_parser("info")
    infoparser.add_argument("plugin", nargs='?', default=None)

    enable_parser = commandparser.add_parser("enable")
    enable_parser.add_argument("plugin", nargs='?', default=None)

    disable_parser = commandparser.add_parser("disable")
    disable_parser.add_argument("plugin", nargs='?', default=None)

    uninstall_parser = commandparser.add_parser("uninstall")
    uninstall_parser.add_argument("plugin", nargs='?', default=None)

    commandparser.add_parser("install")

    args = p.parse_args()

    if(not args.no_logo):
        print(LOGO)

    if(args.command == "list"):
        list_all(args)
    elif(args.command == "enable"):
        enable_plugin(args)
    elif(args.command == "disable"):
        disable_plugin(args)
    elif(args.command == "uninstall"):
        uninstall_plugin(args)
    elif(args.command == "info"):
        plugin_info(args)
    else:
        install(args)

def list_all(args):
    """ Prints out basic plugin informations of all plugins"""
    request_base = upm.RequestBase(scheme=args.scheme,
                                   host=args.host,
                                   port=args.port,
                                   user=args.user,
                                   password=args.password)
    all_plugins = upm.get_all_plugins(request_base, not args.print_all)
    print(f"  {'Name':25} {'Version':13} {'Plugin Key':50}")
    for plugin in all_plugins:
        status = f"{Fore.GREEN}✓{Fore.RESET}" if plugin.enabled else f"{Fore.YELLOW}!{Fore.RESET}"
        plugin_infos = f"{status} {plugin.name[:25]:25}"\
            +f" {str(plugin.version)[:13]:13} ({plugin.key})"
        print(plugin_infos)

def plugin_info(args):
    """ Prints out all available information about a plugin """
    plugin = args.plugin
    if plugin is None:
        plugin = pathutil.get_plugin_key_from_pom()
    if plugin is None:
        logging.error("Could not find the plugin you want to get the info of.")
        sys.exit(1)
    request_base = upm.RequestBase(scheme=args.scheme,
                                   host=args.host,
                                   port=args.port,
                                   user=args.user,
                                   password=args.password)
    info = upm.get_plugin(request_base, plugin)
    info.print_table()

def enable_plugin(args):
    plugin = args.plugin
    if plugin is None:
        plugin = pathutil.get_plugin_key_from_pom()
    if plugin is None:
        logging.error("Could not find the plugin you want to enable.")
        sys.exit(1)
    request_base = upm.RequestBase(scheme=args.scheme,
                                   host=args.host,
                                   port=args.port,
                                   user=args.user,
                                   password=args.password)
    response = upm.enable_disable_plugin(request_base, plugin, True)
    response.print_table()

def disable_plugin(args):
    plugin = args.plugin
    if plugin is None:
        plugin = pathutil.get_plugin_key_from_pom()
    if plugin is None:
        logging.error("Could not find the plugin you want to disable.")
        sys.exit(1)
    request_base = upm.RequestBase(scheme=args.scheme,
                                   host=args.host,
                                   port=args.port,
                                   user=args.user,
                                   password=args.password)
    response = upm.enable_disable_plugin(request_base, plugin, False)
    response.print_table()

def uninstall_plugin(args):
    """ Uninstalls a plugin; If no plugin is given by the url, try to uninstall
    the plugin of the current dir """
    plugin = args.plugin
    if plugin is None:
        plugin = pathutil.get_plugin_key_from_pom()
    if plugin is None:
        logging.error("Could not find the plugin you want to uninstall.")
        sys.exit(1)
    request_base = upm.RequestBase(scheme=args.scheme,
                                   host=args.host,
                                   port=args.port,
                                   user=args.user,
                                   password=args.password)
    status = upm.uninstall_plugin(request_base, plugin)
    if status:
        logging.info("Plugin successfully uninstalled")
    else:
        logging.error("An error occurred. The plugin could not be uninstalled.")



def install(args):
    """ Actual code of the pluploader
    """
    request_base = upm.RequestBase(scheme=args.scheme,
                                   host=args.host,
                                   port=args.port,
                                   user=args.user,
                                   password=args.password)
    try:
        files = {}
        if args.file is None:
            try:
                plugin = pathutil.get_jar_from_pom()
                if plugin is None:
                    raise FileNotFoundError()
                files.update({'plugin': plugin})
            except FileNotFoundError:
               logging.error("Could not find the plugin you want to install. Are you in a maven directory?")
               sys.exit(1)
        else:
            files.update({'plugin': args.file})

        logging.info(f"{os.path.basename(files.get('plugin').name)} will be uploaded \
to {request_base.host}:{request_base.port}")
        if args.interactive:
            confirm = input(
                "Do you really want to upload and install the plugin? (y/N) ")
            if confirm.lower() != "y":
                sys.exit()

        token = upm.get_token(request_base)
        with TqdmUpTo(total=100) as pbar:
            pbar.update_to(0)
            progress, previous_request = upm.upload_plugin(
                request_base, files, token)
            while progress != 100:
                progress, previous_request = upm.get_current_progress(
                    request_base, previous_request)
                pbar.update_to(progress)
                time.sleep(0.1)
        logging.info("plugin uploaded and " +
              ("enabled" if previous_request["enabled"] else "disabled") + "!")
    except Exception as e:
        raise e


if __name__ == "__main__":
    main()
