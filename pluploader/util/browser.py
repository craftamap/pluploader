import webbrowser

import furl


def open_web_upm(base_url: furl.furl):
    url: furl.furl = base_url / "plugins/servlet/upm"
    url.password, url.username = "", ""
    webbrowser.open(str(url))


def open_web_jobs(base_url: furl.furl):
    url: furl.furl = base_url / "admin/scheduledjobs/viewscheduledjobs.action"
    url.password, url.username = "", ""
    webbrowser.open(str(url))
