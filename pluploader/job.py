import logging
import shutil
import sys
import typing

import requests
import typer
from colorama import Fore

from .confluence.jobs import jobs
from .confluence.jobs.jobs import JobsScraper

app_job = typer.Typer()


@app_job.callback()
def job_root(ctx: typer.Context):
    """ Manage and Run Jobs (Confluence only - Beta feature)
    In order to use this feature, it is required that you users locale is set to english
    """


@app_job.command("list")
def job_list(
    ctx: typer.Context,
    hide_default: typing.Optional[bool] = typer.Option(False),
    print_all_infos: typing.Optional[bool] = typer.Option(False),
):
    """ Confluence only, list all jobs available
    """
    try:
        jobs_scraper = JobsScraper(ctx.obj.get("base_url"))

        logging.info("Getting jobs... This can take some time - please wait!")
        _job_list, token = jobs_scraper.list_jobs()

        columns, _ = shutil.get_terminal_size(fallback=(80, 24))

        width = int((columns - 17) / 4)
        print(
            f"{Fore.LIGHTBLACK_EX}{'idx':3} {'name':{width}} {'group':{width*2}} {'id':{width}} {'STS':3} {'RUNBL':5}"
            f"{Fore.RESET}"
        )
        if print_all_infos:
            print(
                f"{Fore.LIGHTBLACK_EX}        {'last execution':{width}} {'next execution':{width}} {'avg duration':7}"
                f"{Fore.RESET}"
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
            if 0 <= int(_idx) < len(_job_list):
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
        jobs_scraper = JobsScraper(ctx.obj.get("base_url"))
        _job_list, token = jobs_scraper.list_jobs()

        selected_job = _select_job(_job_list, idx, id, group)

        logging.info(f"Job {selected_job.name} ({selected_job.id}) selected - Trying to run the job now")

        success = jobs_scraper.run_job(selected_job, token)
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
        jobs_scraper = JobsScraper(ctx.obj.get("base_url"))

        logging.info("Getting jobs... This can take some time - please wait!")
        _job_list, token = jobs_scraper.list_jobs()

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
        jobs_scraper = JobsScraper(ctx.obj.get("base_url"))

        logging.info("Getting jobs... This can take some time - please wait!")
        _job_list, token = jobs_scraper.list_jobs()

        selected_job = _select_job(_job_list, idx, id, group)

        logging.info(f"Job {selected_job.name} ({selected_job.id}) selected - Trying to disable the job now")

        success = jobs.disable_job(selected_job, token)
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
        jobs_scraper = JobsScraper(ctx.obj.get("base_url"))

        logging.info("Getting jobs... This can take some time - please wait!")
        _job_list, token = jobs_scraper.list_jobs()

        selected_job = _select_job(_job_list, idx, id, group)

        logging.info(f"Job {selected_job.name} ({selected_job.id}) selected - Trying to enable the job now")

        success = jobs_scraper.enable_job(selected_job, token)
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
