""" Module implementing the "Scheduled Jobs" functionality of Confluence Server
"""

import dataclasses
import typing

import requests
from bs4 import BeautifulSoup
from furl import furl


@dataclasses.dataclass()
class Job:
    name: str
    group: str
    id: str
    status: str
    last_execution: typing.Optional[str]
    next_execution: typing.Optional[str]
    avg_duration: typing.Optional[int]
    has_history: bool
    is_runnable: bool
    is_editable: bool
    action_enable_disable: typing.Optional[str]
    is_cron: bool
    cron_expression: typing.Optional[str]
    repeat_interval: typing.Optional[str]


class JobsScraper:
    LIST_JOBS_ACTION_URL = "/admin/scheduledjobs/viewscheduledjobs.action"
    RUN_JOB_ACTION_URL = "/admin/scheduledjobs/runJob.action"
    DISABLE_JOB_ACTION_URL = "/admin/scheduledjobs/disableJob.action"
    ENABLE_JOB_ACTION_URL = "/admin/scheduledjobs/enableJob.action"

    def __init__(self, base_url: furl):
        self.base_url: furl = base_url
        self.session = requests.Session()

    def get_token(self) -> str:
        request_url = self.base_url.copy()
        request_url.add(path=self.LIST_JOBS_ACTION_URL)
        response = self.session.get(request_url)
        soup = BeautifulSoup(response.content, "html.parser")
        token = soup.select_one("meta#atlassian-token")["content"]
        return (token, response.cookies)

    def list_jobs(self) -> typing.Tuple[typing.List[Job], str]:
        """
        Returns:
            - list of jobs (typing.List[Job])
            - token(str)
        """
        request_url: furl = self.base_url.copy()
        request_url.add(path=self.LIST_JOBS_ACTION_URL)
        response = self.session.get(request_url)

        soup = BeautifulSoup(response.content, "html.parser")

        token = soup.select_one("meta#atlassian-token")["content"]
        table = soup.select_one("table#schedule-admin")
        headers = [x.text for x in table.select("thead th")]
        table_rows = table.select("tbody tr")

        entries: typing.List[Job] = []
        for row in table_rows:
            job_name = row["data-job-name"]
            job_group = row["data-job-group"]
            job_id = row["data-job-id"]
            is_cron = row["data-is-cron"]
            cron_expression = row["data-cron-expression"]
            repeat_interval = row["data-repeat-interval"]
            has_history = True if row.select_one(".show-history") is not None else False
            is_runnable = True if row.select_one(".run-job") is not None else False
            is_editable = True if row.select_one(".edit-schedule") is not None else False
            has_disable = True if row.select_one(".disable-job") is not None else False
            has_enable = True if row.select_one(".enable-job") is not None else False

            status = row.select("td")[headers.index("Status")].get_text()
            last_execution = row.select("td")[headers.index("Last Execution")].get_text()
            next_execution = row.select("td")[headers.index("Next Execution")].get_text()
            avg_duration = row.select("td")[headers.index("Avg. Duration")].get_text()

            action_enable_disable = None
            if has_disable:
                action_enable_disable = "disable"
            elif has_enable:
                action_enable_disable = "enable"
            entries.append(
                Job(
                    name=job_name,
                    group=job_group,
                    id=job_id,
                    status=status,
                    last_execution=last_execution,
                    next_execution=next_execution,
                    avg_duration=avg_duration,
                    has_history=has_history,
                    is_runnable=is_runnable,
                    is_editable=is_editable,
                    action_enable_disable=action_enable_disable,
                    is_cron=is_cron,
                    cron_expression=cron_expression,
                    repeat_interval=repeat_interval,
                )
            )

        return (entries, token)

    def run_job(self, job: Job, token: typing.Optional[str] = None) -> bool:
        if token is None:
            token = self.get_token()
        request_url = self.base_url.copy()
        request_url.add(path=self.RUN_JOB_ACTION_URL)
        request_url.add(args={"group": job.group, "id": job.id, "atl_token": token})
        response = self.session.get(request_url)
        return response.status_code == 200

    def disable_job(self, job: Job, token: typing.Optional[str] = None,) -> bool:
        if token is None:
            token = self.get_token()
        request_url = self.base_url.copy()
        request_url.add(path=self.DISABLE_JOB_ACTION_URL)
        request_url.add(args={"group": job.group, "id": job.id, "atl_token": token})
        response = self.session.get(request_url)
        return response.status_code == 200

    def enable_job(self, job: Job, token: typing.Optional[str] = None,) -> bool:
        if token is None:
            token = self.get_token()
        request_url = self.base_url.copy()
        request_url.add(path=self.ENABLE_JOB_ACTION_URL)
        request_url.add(args={"group": job.group, "id": job.id, "atl_token": token})
        response = requests.get(request_url)
        return response.status_code == 200
