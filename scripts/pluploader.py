import requests
import xml.etree.ElementTree as ET
import json
import time
from tqdm import tqdm
from colorama import Fore
from pluploader import pathutil
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

def get_filename_from_pom():
    rootdir = pathutil.find_maven_project_root(".")
    ns = {"ns":"http://maven.apache.org/POM/4.0.0"}
    root = ET.parse(f'{rootdir}/pom.xml').getroot()
    artifactId =  root.find("ns:artifactId", ns).text
    version =  root.find("ns:version", ns).text
    return f"{artifactId}-{version}.jar"


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

    try:
        token_url = furl()
        token_url.set(scheme=args.scheme, host=args.host, port=args.port, path=PATH)
        token_url.set(username= args.user, password=args.password)
        token_url.set(args={"os_authType":"basic"})
        print(token_url)
        token_response = requests.head(token_url.url)
        token = token_response.headers['upm-token']
        print(token)
        files = {}
        if args.file is None:
            plugin_name = get_filename_from_pom()
            files.update({'plugin': open(f"target/{plugin_name}", 'rb')})
        else:
            files.update({'plugin': args.file})
        upload_url = furl()
        upload_url.set(scheme=args.scheme, host=args.host, port=args.port, path=PATH)
        upload_url.set(username=args.user, password=args.password)
        upload_url.set(args={"token": token})
        with TqdmUpTo(total=100) as pbar:
            pbar.update_to(0)
            upload_response = requests.post(upload_url.url, files=files)
            pbar.update_to(50)
            upload_response_data = json.loads(upload_response.text.replace("<textarea>", "").replace("</textarea>", ""))
            while True:
                if ("type" in upload_response_data):
                    pbar.update_to(upload_response_data["status"]["amountDownloaded"] if "amountDownloaded" in upload_response_data["status"] else 0)
                    time.sleep(upload_response_data['pingAfter']/200)
                    upload_url = furl()
                    upload_url.set(scheme=args.scheme, host=args.host, port=args.port, path=upload_response_data["links"]["self"])
                    upload_url.set(username=args.user, password=args.password)
                    upload_response_data = requests.get(upload_url.url).json()
                else:
                    pbar.update_to(100)
                    break
        print ("Plugin hochgeladen und "+("enabled" if upload_response_data["enabled"] else "disabled")+"!")
    except Exception as e:
        print(e)
    finally:
        pass





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
