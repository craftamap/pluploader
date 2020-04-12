""" pluploader executable
"""

import time
import sys
import os.path
import configargparse
from tqdm import tqdm
from colorama import Fore

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
{Fore.YELLOW}            {Fore.RED}({Fore.GREEN}|||||{Fore.YELLOW})
{Fore.RESET}"""


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
    print(LOGO)
    project_root = pathutil.find_maven_project_root(".")
    config_locations = ["~/.pluprc"]

    if project_root is not False:
        config_locations.append(os.path.join(project_root, ".pluprc"))
    p = configargparse.ArgParser(
        default_config_files=config_locations,
        config_file_parser_class=configargparse.YAMLConfigFileParser)
    commandparser = p.add_subparsers(dest="command")
    commandparser.add_parser("install")
    commandparser.add_parser("list")

    p.add("--host", default="localhost")
    p.add("--scheme", default="http")
    p.add("--user", required=True)
    p.add("--password", required=True)
    p.add("--port", default="8090")
    p.add("-i", "--interactive", default=False, action='store_true')
    p.add("-f", "--file", type=configargparse.FileType("rb"))
    args = p.parse_args()
    if(args.command == "list"):
        list_all(args)
    else:
        install(args)

def list_all(args):
    request_base = upm.RequestBase(scheme=args.scheme,
                                   host=args.host,
                                   port=args.port,
                                   user=args.user,
                                   password=args.password)
    all_plugins = upm.get_all_plugins(request_base)
    print(f"  {'Name':25} {'Version':13} {'Plugin Key':50}")
    for plugin in all_plugins:
        status = f"{Fore.GREEN}✓{Fore.RESET}" if plugin.enabled else f"{Fore.YELLOW}!{Fore.RESET}"
        plugin_info = f"{status} {plugin.name[:25]:25} {str(plugin.version)[:13]:13} ({plugin.key:50})"
        print(plugin_info)

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
            plugin = pathutil.get_jar_from_pom()
            if plugin is None:
                print("File not found!")
                sys.exit(1)
            files.update({'plugin': plugin})
        else:
            files.update({'plugin': args.file})

        print(f"{os.path.basename(files.get('plugin').name)} will be uploaded \
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
        print("plugin uploaded and " +
              ("enabled" if previous_request["enabled"] else "disabled") + "!")
    except Exception as e:
        raise e


if __name__ == "__main__":
    main()
