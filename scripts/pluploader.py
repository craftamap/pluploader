import requests
import xml.etree.ElementTree as ET
import json
import time
from tqdm import tqdm

USER = "admin"
PASSWD = "admin"
HOST="localhost:8090"

PATH = "/rest/plugins/1.0/"


SCANDIO = """ssssss....
 SSSSSSSSSSSSSSS.
  SSSSS°°°   °°SSs
  SSSS          SSS
  SSS            SSS
  SSS     cc     SSS
  SSS.    °°    .SSS
   SSS          SSS
    SSSs      sSSS
     °SSSSssSSS°
         °°°°
"""

def get_filename_from_pom():
    ns = {"ns":"http://maven.apache.org/POM/4.0.0"}
    root = ET.parse('pom.xml').getroot()
    artifactId =  root.find("ns:artifactId", ns).text
    version =  root.find("ns:version", ns).text
    return f"{artifactId}-{version}.jar"


def main():
    print(SCANDIO)
    try:
        plugin_name = get_filename_from_pom()

        token_response = requests.head(f"http://{USER}:{PASSWD}@{HOST}{PATH}?os_authType=basic")
        token = token_response.headers['upm-token']
        print(token)
        files={'plugin': open(f"target/{plugin_name}", 'rb')}
        upload_response = requests.post(f"http://{USER}:{PASSWD}@{HOST}{PATH}?token={token}", files=files)
        upload_response_data = json.loads(upload_response.text.replace("<textarea>", "").replace("</textarea>", ""))
        with TqdmUpTo(total=100) as pbar:
            while True:
                if ("type" in upload_response_data):
                    pbar.update_to(((upload_response_data["status"]["amountDownloaded"] -50)*2) if "amountDownloaded" in upload_response_data["status"] else 0)
                    time.sleep(upload_response_data['pingAfter']/200)
                    upload_response_data = requests.get(f"http://{USER}:{PASSWD}@{HOST}"+upload_response_data["links"]["self"]).json()
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
