import logging
import sys
from enum import Enum

import requests
import typer

from .upm.upmapi import UpmApi
from .util import pathutil

app_license = typer.Typer()


timebomb_licenses = {
    "threehours": (
        "AAABCA0ODAoPeNpdj01PwkAURffzKyZxZ1IyUzARkllQ24gRaQMtGnaP8VEmtjPNfFT59yJVFyzfubkn796Ux0Bz6SmbUM5nbDzj97RISxozHpMUnbSq8"
        "8poUaLztFEStUN6MJZ2TaiVpu/YY2M6tI6sQrtHmx8qd74EZ+TBIvyUU/AoYs7jiE0jzknWQxMuifA2IBlUbnQ7AulVjwN9AaU9atASs69O2dNFU4wXJL"
        "c1aOUGw9w34JwCTTZoe7RPqUgep2X0Vm0n0fNut4gSxl/Jcnj9nFb6Q5tP/Ueu3L+0PHW4ghZFmm2zZV5k6/95CbR7Y9bYGo/zGrV3Ir4jRbDyCA6vt34"
        "DO8p3SDAsAhQnJjLD5k9Fr3uaIzkXKf83o5vDdQIUe4XequNCC3D+9ht9ZYhNZFKmnhc=X02dh"
    ),
    "sixtyseconds": (
        "AAABEA0ODAoPeNp9UE1Pg0AUvO+v2MSbCc0uQZOS7KEIUWMtpNJqGi9bfKUb4S3ZD7T/XgrqwYPv9mbezGTeRXn0NK8cZRHlPGZRHEW0SEsaMh6SFGxlV"
        "OeURlGCdbRRFaAFetCGdo2vFdI36KHRHRhLVr7dg8kPGztsgjNyY0Cexal0IELOw4DNA85J1svGj4xwxgOZrOzsciYrp3qY0Eep0AFKrCD77JQ5jTapN6"
        "PyNb5mw5Dc1BKVndwWrpHWKonkCUwP5j4Vye28DF422yh42O3ugoTxZ7KcagzsBt9Rf+AP8k/O90V56mAl24HPttkyL7L1b+1Etnut19BqB4sa0FkRXpH"
        "Cm+ooLfz9wRfgrX9WMCwCFAkWHvhJCdutS3LcZ46iYgICDPQqAhQL76vdT4AYTQXBwl/wbw/MtQrP4w==X02dt"
    ),
    "tenseconds": (
        "AAABEA0ODAoPeNp9UE1Pg0AUvO+v2MSbCc0uoYeScChC1FhLU6Gaxsvr+ko3wi7ZD7T/XoTqwYPv9mbezGTeVXnytBCOsohyHrN5HHG6yUoaMh6SDK0ws"
        "nNSq6RE62gjBSqL9KgN7RpfS0XfsMdGd2gsWfv2gKY4VnbYEs7IjUH4FmfgMAk5DwO2CDgneQ+NH5nEGY9ksrKz6xkIJ3uc0EeQyqECJTD/7KQ5jzaZN6"
        "PyNeZsGFKYGpS0k9vSNWCtBEWe0PRo7rMkvV2UwUu1i4KH/f4uSBl/JqupxsBW6l3pD/WD/JNzuSjPHa6hHfh8l6+KTb79rZ1Ce9B6i612uKxROZuEc7L"
        "xRpzA4t8ffAHYfn9KMCwCFEErfsC777XOAsdjoKVRM24pJL3+AhRbORJTyFn7+5BUotohYeGfCqYgkA==X02dt"
    ),
}


class TimebombLicensesEnum(str, Enum):
    threehours = "threehours"
    sixtyseconds = "sixtyseconds"
    tenseconds = "tenseconds"


@app_license.callback()
def safemode(ctx: typer.Context):
    """ Get and set license information for apps
    """


@app_license.command("info")
def info(ctx: typer.Context, plugin: str = typer.Argument(None, help="the plugin key")):
    if plugin is None:
        try:
            plugin = pathutil.get_plugin_key_from_pom()
        except FileNotFoundError:
            logging.error("Could not find the plugin you want to get the license info of. Are you in a maven directory?")
            sys.exit(1)
        except pathutil.PluginKeyNotFoundError:
            logging.error(
                "Could not find the plugin you want to get the license info of. Is the plugin key set in the pom.xml?"
            )
            sys.exit(1)
    try:
        upm = UpmApi(ctx.obj.get("base_url"))
        license = upm.get_license(plugin)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    for key, value in license.__dict__.items():
        print(f"{(key.replace('_', ' ') + ':'):25.25} {value}")


@app_license.command("update")
def update(
    ctx: typer.Context,
    plugin: str = typer.Argument(None, help="the plugin key"),
    license: str = typer.Option(..., help="the license you want to update"),
):
    if plugin is None:
        try:
            plugin = pathutil.get_plugin_key_from_pom()
        except FileNotFoundError:
            logging.error("Could not find the plugin you want to update the license of. Are you in a maven directory?")
            sys.exit(1)
        except pathutil.PluginKeyNotFoundError:
            logging.error("Could not find the plugin you want to update the license of. Is the plugin key set in the pom.xml?")
            sys.exit(1)
    try:
        upm = UpmApi(ctx.obj.get("base_url"))
        license = upm.update_license(plugin, license)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    for key, value in license.__dict__.items():
        print(f"{(key.replace('_', ' ') + ':'):25.25} {value}")


@app_license.command("delete")
def delete(
    ctx: typer.Context, plugin: str = typer.Argument(None, help="the plugin key"),
):
    if plugin is None:
        try:
            plugin = pathutil.get_plugin_key_from_pom()
        except FileNotFoundError:
            logging.error("Could not find the plugin you want to delete the license of. Are you in a maven directory?")
            sys.exit(1)
        except pathutil.PluginKeyNotFoundError:
            logging.error("Could not find the plugin you want to delete the licence of. Is the plugin key set in the pom.xml?")
            sys.exit(1)
    try:
        upm = UpmApi(ctx.obj.get("base_url"))
        license = upm.delete_license(plugin)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    for key, value in license.__dict__.items():
        print(f"{(key.replace('_', ' ') + ':'):25.25} {value}")
    logging.warn(
        "When the delete command is run, the old license is shown. Please run pluploader license info to ensure that"
        " removing the license was successful."
    )


@app_license.command("timebomb")
def timebomb(
    ctx: typer.Context,
    plugin: str = typer.Argument(None, help="the plugin key"),
    timebomb: TimebombLicensesEnum = typer.Option(TimebombLicensesEnum.threehours, case_sensitive=False),
):
    if plugin is None:
        try:
            plugin = pathutil.get_plugin_key_from_pom()
        except FileNotFoundError:
            logging.error("Could not find the plugin you want to update the license of. Are you in a maven directory?")
            sys.exit(1)
        except pathutil.PluginKeyNotFoundError:
            logging.error("Could not find the plugin you want to update the license of. Is the plugin key set in the pom.xml?")
            sys.exit(1)
    try:
        upm = UpmApi(ctx.obj.get("base_url"))
        license = upm.update_license(plugin, timebomb_licenses[timebomb])
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    for key, value in license.__dict__.items():
        print(f"{(key.replace('_', ' ') + ':'):25.25} {value}")
