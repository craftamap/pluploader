import requests
from requests.auth import HTTPBasicAuth
import json
import time
from tqdm import tqdm
from colorama import Fore
from pluploader import pathutil
from pluploader import upmapi as upm
import configargparse
import os.path
from furl import furl

USER = "admin"
PASSWD = "admin"
HOST="localhost:8090"

PATH = "/rest/plugins/1.0/"


LOGO = f"""{Fore.YELLOW}
SSSSssssss...   {Fore.RED}s{Fore.RESET}
{Fore.YELLOW}SSSSSSSSSSSSSss{Fore.RED}sSs{Fore.RESET}
{Fore.YELLOW}SSSSS°°°   °°SSS{Fore.RED}SS{Fore.RESET}
{Fore.YELLOW}SSSS    {Fore.WHITE}..{Fore.YELLOW}    SSS{Fore.RED}S{Fore.RESET}
{Fore.YELLOW}SSS    {Fore.WHITE}ssss{Fore.YELLOW}    SSS
SSS     {Fore.WHITE}cc{Fore.YELLOW}     SSS
SSS.    {Fore.WHITE}°°{Fore.YELLOW}    .SSS
 SSS          SSS
 SSSSs      sSSS
{Fore.LIGHTGREEN_EX}sSS{Fore.YELLOW}SSSSSssSSS°
{Fore.LIGHTGREEN_EX}  ssss{Fore.YELLOW}sssss{Fore.RESET}
"""

def main():
    print(LOGO)
    project_root = pathutil.find_maven_project_root(".")
    config_locations = ["~/.pluprc"]

    if project_root is not False:
        config_locations.append(os.path.join(project_root, ".pluprc"))
    p = configargparse.ArgParser(default_config_files=config_locations,
                                 config_file_parser_class=configargparse.YAMLConfigFileParser)
    p.add("--host", default="localhost")
    p.add("--scheme", default="http")
    p.add("--user", required=True)
    p.add("--password", required=True)
    p.add("--port", default="8090")
    p.add("-f", "--file", type=configargparse.FileType("rb"))
    args = p.parse_args()

    request_base = upm.RequestBase(scheme=args.scheme, host=args.host, port=args.port,
                                   user=args.user, password=args.password)
    try:
        token = upm.get_token(request_base)
        files = {}
        if args.file is None:
            plugin_name = pathutil.get_jar_from_pom()
            files.update({'plugin': open(f"target/{plugin_name}", 'rb')})
        else:
            files.update({'plugin': args.file})
        with TqdmUpTo(total=100) as pbar:
            pbar.update_to(0)
            progress, previous_request = upm.upload_plugin(request_base, files, token)
            while progress != 100:
                progress, previous_request = upm.get_current_progress(request_base,
                                                                      previous_request)
                pbar.update_to(progress)
        print("Plugin hochgeladen und "+("enabled" if previous_request["enabled"] else "disabled")+"!")
    except Exception as e:
        raise e





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
