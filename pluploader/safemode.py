import typer
from colorama import Fore
import logging
import requests
import sys

from .upm import upmapi as upm

app_safemode = typer.Typer()


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
