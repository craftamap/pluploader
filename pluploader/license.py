import logging
import sys
from enum import Enum

import requests
import typer
from rich.console import Console
from rich.table import Table

from .upm.upmapi import UpmApi
from .upm.upmcloudapi import Token, UpmCloudApi
from .util import browser, pathutil

app_license = typer.Typer()

app_access_token = typer.Typer()
app_license.add_typer(app_access_token, name="access-token")

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
def license(ctx: typer.Context):
    """Get and set license information for apps"""


@app_license.command("info")
def info(
    ctx: typer.Context,
    plugin: str = typer.Argument(None, help="the plugin key"),
    web: bool = typer.Option(False, help="open upm in web browser after showing info"),
):
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
    grid = Table.grid(expand=True)
    grid.add_column(style="blue")
    grid.add_column()
    for key, value in license.__dict__.items():
        grid.add_row(key.replace("_", " "), f"{value}")
    console = Console()
    console.print(grid)
    if web:
        browser.open_web_upm(ctx.obj.get("base_url"))


@app_license.command("update")
def update(
    ctx: typer.Context,
    plugin: str = typer.Argument(None, help="the plugin key"),
    license: str = typer.Option(..., help="the license you want to update"),
    web: bool = typer.Option(False, help="open upm in web browser after updating license"),
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
    grid = Table.grid(expand=True)
    grid.add_column(style="blue")
    grid.add_column()
    for key, value in license.__dict__.items():
        grid.add_row(key.replace("_", " "), f"{value}")
    console = Console()
    console.print(grid)
    if web:
        browser.open_web_upm(ctx.obj.get("base_url"))


@app_license.command("delete")
def delete(
    ctx: typer.Context,
    plugin: str = typer.Argument(None, help="the plugin key"),
    web: bool = typer.Option(False, help="open upm in web browser after deleting license"),
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
    grid = Table.grid(expand=True)
    grid.add_column(style="blue")
    grid.add_column()
    for key, value in license.__dict__.items():
        grid.add_row(key.replace("_", " "), f"{value}")
    console = Console()
    console.print(grid)
    logging.warn(
        "When the delete command is run, the old license is shown. Please run pluploader license info to ensure that"
        " removing the license was successful."
    )
    if web:
        browser.open_web_upm(ctx.obj.get("base_url"))


@app_license.command("timebomb")
def timebomb(
    ctx: typer.Context,
    plugin: str = typer.Argument(None, help="the plugin key"),
    timebomb: TimebombLicensesEnum = typer.Option(TimebombLicensesEnum.threehours, case_sensitive=False),
    web: bool = typer.Option(False, help="open upm in web browser applying timebomb license"),
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
    grid = Table.grid(expand=True)
    grid.add_column(style="blue")
    grid.add_column()
    for key, value in license.__dict__.items():
        grid.add_row(key.replace("_", " "), f"{value}")
    console = Console()
    console.print(grid)
    if web:
        browser.open_web_upm(ctx.obj.get("base_url"))


@app_access_token.callback()
def access_token(ctx: typer.Context):
    """Get and set information about cloud access tokens"""


@app_access_token.command("list")
def access_token_list(
    ctx: typer.Context, web: bool = typer.Option(False, help="open upm in web browser after showing info"),
):
    """lists all access tokens for the instance"""
    try:
        upm = UpmCloudApi(ctx.obj.get("base_url"))
        access_tokens = upm.list_access_token()
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    table = Table(expand=True)
    table.add_column("pluginKey", style="blue")
    table.add_column("token")
    table.add_column("state")
    table.add_column("valid")
    for access_token in access_tokens:
        table.add_row(access_token.pluginKey, access_token.token, access_token.state, f"{access_token.valid}")
    console = Console()
    console.print(table)
    if web:
        browser.open_web_upm(ctx.obj.get("base_url"))


@app_access_token.command("info")
def access_token_info(
    ctx: typer.Context,
    plugin: str = typer.Argument(None, help="the plugin key"),
    web: bool = typer.Option(False, help="open upm in web browser after showing info"),
):
    """get information about a specific access token by specifing the plugin key"""
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
        upm = UpmCloudApi(ctx.obj.get("base_url"))
        access_token = upm.get_access_token(plugin)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)
    table = Table(expand=True)
    table.add_column("pluginKey", style="blue")
    table.add_column("token")
    table.add_column("state")
    table.add_column("valid")
    for t in [access_token]:
        table.add_row(t.pluginKey, t.token, t.state, f"{t.valid}")
    console = Console()
    console.print(table)
    if web:
        browser.open_web_upm(ctx.obj.get("base_url"))


@app_access_token.command("update")
def access_token_update(
    ctx: typer.Context,
    plugin: str = typer.Argument(None, help="the plugin key"),
    token: str = typer.Option(..., help="the access token"),
    web: bool = typer.Option(False, help="open upm in web browser after showing info"),
    state: Token.TokenState = typer.Option(Token.TokenState.ACTIVE_SUBSCRIPTION.value),
):
    """get information about a specific access token by specifing the plugin key"""
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
        upm = UpmCloudApi(ctx.obj.get("base_url"))
        if not token:
            logging.warn("empty access token specified. Deleting access token")
            upm.delete_access_token(plugin)
            logging.warn("Access Token successfully deleted")
            return

        access_token = upm.update_access_token(plugin, token, state)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)

    table = Table(expand=True)
    table.add_column("pluginKey", style="blue")
    table.add_column("token")
    table.add_column("state")
    table.add_column("valid")
    for t in [access_token]:
        table.add_row(t.pluginKey, t.token, t.state, f"{t.valid}")
    console = Console()
    console.print(table)
    if web:
        browser.open_web_upm(ctx.obj.get("base_url"))


@app_access_token.command("delete")
def access_token_delete(
    ctx: typer.Context,
    plugin: str = typer.Argument(None, help="the plugin key"),
    web: bool = typer.Option(False, help="open upm in web browser after showing info"),
):
    """get information about a specific access token by specifing the plugin key"""
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
        upm = UpmCloudApi(ctx.obj.get("base_url"))
        logging.info("Deleting access token")
        upm.delete_access_token(plugin)
        logging.info("Access Token successfully deleted")

    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to host - check your base-url")
        sys.exit(1)
    except Exception as exc:
        logging.error("An error occured - check your credentials")
        logging.error("%s", exc)
        sys.exit(1)

    if web:
        browser.open_web_upm(ctx.obj.get("base_url"))
