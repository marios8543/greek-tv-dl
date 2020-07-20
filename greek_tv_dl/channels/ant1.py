#Antenna.gr Downloader - marios8543 | github.com/marios8543
#MIT License

from aiohttp import ClientSession
from aiofiles import open as aopen
from asyncio import get_event_loop, Semaphore, sleep, Event
from os import getenv, path, mkdir
from sys import argv
from logging import info, error, debug, warn, basicConfig, INFO
from pyquery import PyQuery

web = ClientSession()
basicConfig(level=INFO)

class Segment:
    def __init__(self, url, title, idx):
        self.url = url
        self.title = title
        self.idx = idx

        self.res = None

    async def get(self):
        c = 0
        while True:
            res = await web.get(self.url)
            if res.status == 200:
                self.res = await res.read()
                return
            error("Could not get segment {} of {} ({}: {}). Retrying...".format(self.idx+1, self.title, res.status, await res.text()))
            c += 1
            if c == int(getenv("MAX_SEG_RETRIES", "3")):
                error("Failed to get segment {} of {}. Skipping...".format(self.idx+1, self.title))
                return
            await sleep(10)

class Player:
    def __init__(self, dc):
        self.title = dc['title']
        self.url = dc['url']
        self.show = dc['Show']

        self.dl_queue = []
        self.dl_sem = Semaphore(int(getenv("MAX_DOWNLOADS", "8")))

    async def download(self, save_dir=""):
        if path.isfile(path.join(save_dir, self.show, self.title+".ts")):
            info("{}.ts exists. Skipping...".format(self.title))
            return
        info("Commencing download of {}".format(self.title))
        await self._populate_segments(await self._get_master_url())
        await self._downloader(save_dir)
        await self._saver(save_dir)

    async def _get_master_url(self):
        res = await web.get(self.url)
        if res.status == 200:
            res = await res.text()
            url = res.splitlines(False)[2]
            if not url.startswith("https://"):
                raise ValueError("Could not parse master.m3u8")
            debug("Got master URL: {}".format(url))
            return url
        raise ValueError("Could not get master.m3u8")

    async def _populate_segments(self, master_url):
        res = await web.get(master_url)
        if res.status == 200:
            debug("Populating download queue with segments")
            res = (await res.text()).splitlines(False)
            i = 0
            for v in res:
                if v.startswith("https://"):
                    self.dl_queue.append(Segment(v, self.title, i))
                    i+=1
            return
        raise ValueError("Could not get segments")
    
    async def _downloader(self, save_dir):
        debug("Starting downloader coroutine")
        ev = Event()
        _i = [0]
        def inc():
            _i[0] += 1
            if _i[0] == len(self.dl_queue):
                ev.set()
        for item in self.dl_queue:
            await self.dl_sem.acquire()
            get_event_loop().create_task(item.get()).add_done_callback(lambda _: (
                self.dl_sem.release(),
                inc()
            ))
        await ev.wait()
        info("Downloaded {}. Saving...".format(self.title))
    
    async def _saver(self, save_dir):
        try:
            mkdir(path.join(save_dir, self.show))
        except:
            pass
        async with aopen(path.join(save_dir, self.show, self.title)+".ts", "wb+") as f:
            for item in self.dl_queue:
                if item.res:
                    await f.write(item.res)
        info("Saved {}.".format(self.title))

async def get_player(cid):
    res = await web.get("https://www.antenna.gr/templates/data/player", params={"cid": cid})
    if res.status == 200:
        show = Player(await res.json())
        debug("Got player for CID {}".format(cid))
        return show
    raise ValueError("Could not parse player: {}".format(await res.text()))

class Episode:
    def __init__(self, el):
        self.link = el.attrib["href"]
        el = PyQuery(el)(".content-container")
        self.title = el.find("h2").text()

    def get_id(self):
        return self.link.split("/")[2]

    async def download(self, save_dir=""):
        player = await get_player(self.get_id())
        await player.download(save_dir)

    def __str__(self):
        return self.title

class Show:
    def __init__(self, el):
        a = el.find("a")
        self.link = a.attrib["href"]
        div = PyQuery(el)(".title-container")
        self.title = div.find("h2").text()

    async def get_aid(self):
        res = await web.get("https://www.antenna.gr{}/videos".format(self.link))
        if res.status == 200:
            txt = await res.text()
            for l in txt.splitlines():
                if "?aid=" in l:
                    return l.split("?aid=")[1][:-1]
        raise RuntimeError("Could not fetch AID of series")

    async def get_episodes(self):
        page = 1
        ids = []
        aid = await self.get_aid()
        while True:
            res = await web.get("https://www.antenna.gr/templates/data/morevideos", params={"aid":aid, "p":page})
            if res.status == 200:
                root = PyQuery(await res.text())
                l= []
                for el in root.find("article"):
                    el = el.find("a")
                    l.append(Episode(el))
                ids.extend(l)
                if not l:
                    break
            page+=1
        ids.reverse()
        return ids

    def __str__(self):
        return self.title

async def get_shows():
    letters = ("Α","Β","Γ","Δ","Ε","Ζ","Η","Θ","Ι","Κ","Λ","Μ","Ν","Ξ","Ο","Π","Ρ","Σ","Τ","Υ","Φ","Χ","Ψ","Ω")
    s = []
    for l in letters:
        res = await web.get("https://www.antenna.gr/shows/{}".format(l))
        if res.status == 200:
            try:
                root = PyQuery(await res.text())
                items = root("#contentContainer").find("article")
                for i in items:
                    try:
                        s.append(Show(i))
                    except:
                        warn("Could not parse item in page {}".format(l))
            except:
                warn("Could not parse page for letter {}".format(l))
    return s