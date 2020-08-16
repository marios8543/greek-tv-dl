# pylint: disable=F0401
from greek_tv_dl._version import __VERSION__

from aiohttp.web import Application, Response, json_response, get, _run_app, run_app, WebSocketResponse
from asyncio import new_event_loop, sleep, set_event_loop, get_event_loop, run_coroutine_threadsafe
from logging import error
from random import randint
from os import getenv, name, path
from concurrent.futures import ProcessPoolExecutor
from greek_tv_dl.resources.logo import ICON
import aiohttp_debugtoolbar
from aiohttp.web_runner import GracefulExit
from threading import enumerate as t_enumerate
import ctypes
from greek_tv_dl.main import get_config, set_config

def async_raise(thread_obj, exception):
    target_tid = thread_obj.ident
    if target_tid not in {thread.ident for thread in t_enumerate()}:
        raise ValueError('Invalid thread object, cannot find thread identity among currently active threads.')
    affected_count = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid), ctypes.py_object(exception))
    if affected_count == 0:
        raise ValueError('Invalid thread identity, no thread has been affected.')
    elif affected_count > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid), ctypes.c_long(0))
        raise SystemError("PyThreadState_SetAsyncExc failed, broke the interpreter state.")

app = Application()
aiohttp_debugtoolbar.setup(app)
shows_cache = {}
episodes_cache = {}
jobs = {}

SAVE_DIR = getenv("SAVE_DIR", get_config("save_dir", ""))
_immutable = False

class Job:
    def __init__(self, ids):
        self.episodes = []
        self.now_downloading = None
        for i in ids:
            if i in episodes_cache and not episodes_cache[i].downloading:
                episodes_cache[i].downloading = True
                self.episodes.append(episodes_cache[i])
        self.id = str(randint(100000,999999))
        self.total = len(self.episodes)
        self.task = None
    
    async def _start(self):
        jobs[self.id] = self
        while len(self.episodes) > 0:
            ep = self.episodes.pop(0)
            self.now_downloading = ep
            try:
                await ep.download(save_dir=SAVE_DIR)
            except Exception as e:
                error("Something went wrong while downloading {}. {}".format(ep.title, e))
            episodes_cache[ep.id].downloading = False
        jobs.pop(self.id, None)

    def start(self):
        self.task = get_event_loop().create_task(self._start())

    def get_progress(self):
        return {
            "downloading": self.now_downloading.to_dict(),
            "total": self.total,
            "current": self.total - len(self.episodes)
        }

    def cancel(self):
        self.task.cancel()
        jobs.pop(self.id, None)
        for i in self.episodes:
            episodes_cache[i.id].downloading = False

    def to_dict(self):
        return {
            "id": self.id,
            "now_downloading": self.now_downloading.to_dict(),
            "episodes": [i.to_dict() for i in self.episodes]
        }

async def info(request):
    return Response(status=200, headers={"GreekTvDl-Version": __VERSION__})

async def get_shows(request, dry=False): #Dry run is used to repurpose this as a cache populator instead of http route
    if dry:
        channel = dry
    else:
        channel = request.query.get("channel")
    if channel == "ANT1":
        from greek_tv_dl.channels import ant1 as provider
    elif channel == "Alpha":
        from greek_tv_dl.channels import alpha as provider
    elif channel == "Star":
        from greek_tv_dl.channels import star as provider
    elif channel == "Open":
        from greek_tv_dl.channels import opentv as provider
    else:
        if dry:
            raise ValueError("invalid_channel")
        return Response(body="invalid_channel", status=400)
    
    shows = await provider.get_shows()
    shows_cache[channel] = shows
    if not dry:
        return json_response([i.to_dict() for i in shows])

async def get_episodes(request):
    channel = request.query.get("channel")
    show_id = request.query.get("show_id")
    if not channel in shows_cache:
        await get_shows(None, channel)
    show = next(s for s in shows_cache[channel] if s.id == show_id)
    if not show:
        return Response(body="invalid_show_id", status=404)
    episodes = await show.get_episodes()
    for i in episodes:
        if i.id not in episodes_cache:
            episodes_cache[i.id] = i
    return json_response([i.to_dict() for i in episodes])

async def set_save_dir(request):
    if _immutable:
        return Response(status=403, body="save_dir_immutable")
    global SAVE_DIR
    directory = request.query.get("dir")
    if path.isdir(directory):
        SAVE_DIR = directory
        set_config("save_dir", directory)
        return Response(status=200, body="save_dir_set")

async def add_job(request):
    episode_ids = request.query.get("episode_ids").split(",")
    job = Job(episode_ids)
    job.start()
    return Response(status=200, body=job.id)

async def get_jobs(request):
    return json_response(list(jobs.keys()))

async def get_job_details(request):
    job_id = request.query.get("job_id")
    try:
        return json_response(jobs[job_id].to_dict())
    except KeyError:
        return Response(body="job_not_found", status=404)

async def get_job_progress(request):
    job_id = request.query.get("job_id")
    try:
        return json_response(jobs[job_id].get_progress())
    except KeyError:
        return Response(body="job_not_found", status=404)

async def cancel_job(request):
    job_id = request.query.get("job_id")
    try:
        jobs[job_id].cancel()
        return Response(status=200, body="scheduled_for_cancel")
    except KeyError:
        return Response(body="job_not_found", status=404)

async def ws_handler(request):
    ws = WebSocketResponse()
    await ws.prepare(request)
    while not ws.closed:
        await ws.send_json({
            i: jobs[i].get_progress()
            for i in jobs
        })
        await sleep(int(getenv("SOCKET_INTERVAL", "5")))

app.add_routes([
    get("/info", info),
    get("/get_shows", get_shows),
    get("/get_episodes", get_episodes),
    get("/set_save_dir", set_save_dir),
    get("/add_job", add_job),
    get("/get_jobs", get_jobs),
    get("/get_job_details", get_job_details),
    get("/get_job_progress", get_job_progress),
    get("/cancel_job", cancel_job),
    get("/socket", ws_handler)
])

def setup_systray():
    from pystray import Icon, Menu, MenuItem
    from subprocess import Popen
    icon = Icon("Greek TV Downloader")
    def stop():
        async_raise(icon._setup_thread, SystemExit())
        icon.stop()
    menu = Menu(
        MenuItem("Άνοιγμα", lambda: Popen('START /B "" greek-tv-dl' if name=='nt' else "greek-tv-dl", shell=True)),
        MenuItem("Εργασίες", lambda: Popen('START /B "" greek-tv-dl --jobs' if name=='nt' else "greek-tv-dl --jobs", shell=True)),
        MenuItem("Έξοδος", stop)
    )
    icon._icon = ICON
    icon._menu = menu
    return icon

def get_task(host, port, *args, **kwargs):
    return _run_app(app, host=host, port=port, *args, **kwargs)

def run(host, port, systray=True, *args, **kwargs):
    if systray:
        icon = setup_systray()
        def _(i):
            i.visible = True
            set_event_loop(new_event_loop())
            run_app(app, host=host, port=port, *args, **kwargs)
        icon.run(_)
    else:
        run_app(app, host=host, port=port, *args, **kwargs)