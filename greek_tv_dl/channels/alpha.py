from aiohttp import ClientSession
from pyquery import PyQuery
from json import loads
from logging import error, warn, info, basicConfig, INFO
from os import mkdir, path
from aiofiles import open as aopen

basicConfig(level=INFO)
web = ClientSession()
vid_link_cache = {}

class Episode:
    def __init__(self, el, show, year):
        self.video_id = str(loads(el.attrib["data-plugin-openplayer"])["WebTvVideoId"])
        self.title = el.text.strip()
        self.show = show
        self.year = year

    async def _populate_links(self):
        page = 1
        while True:
            res = await web.get("https://www.alphatv.gr/ajax/Isobar.AlphaTv.Components.PopUpVideo.PopUpVideo.PlayMedia/", params={
                "vid": self.video_id,
                "showId": self.show.sid,
                "year": self.year,
                "pg": page
            })
            if res.status == 200:
                root = PyQuery(await res.text())("a[data-plugin-openplayer]")
                c = 0
                for el in root:
                    meta = loads(el.attrib['data-plugin-openplayer'])
                    if "Url" in meta:
                        vid_link_cache[str(meta['Id'])] = meta['Url']
                        c += 1
                if not c:
                    break
            page += 1

    async def download(self, save_dir=""):
        try:
            vid_link_cache[str(self.video_id)]
        except KeyError as e:
            info("Could not find VID {}. Fetching...".format(e))
            await self._populate_links()
        url = vid_link_cache[str(self.video_id)]
        try:
            mkdir(path.join(save_dir, self.show.title))
        except:
            pass
        res = await web.get(url)
        if res.status == 200:
            async with aopen(path.join(save_dir, self.show.title, self.title)+".mp4", "wb+") as f:
                while True:
                    part = await res.content.read(1024)
                    if not part:
                        break
                    await f.write(part)
                info("Downloaded and saved {}".format(self.title))
                return
        

    def __str__(self):
        return self.title

class Show:
    def __init__(self, el):
        self.link = el.attrib["href"]
        self.title = PyQuery(el)(".tvShowImg").find("h3").text()
        self.sid = None
        self.years = []
        
    async def get_sid_year(self):
        if self.sid and self.years:
            return self.sid, self.years
        res = await web.get(self.link)
        if res.status == 200:
            lines = (await res.text()).splitlines(False)
            for l in lines:
                if "window.Environment.showId = " in l:
                    sid = l.split("window.Environment.showId = ")[1][:-1]
                    break
            years = list(set([i.attrib["key"] for i in PyQuery(await res.text())("a[category-parentid='gallery']")]))
            years.sort()
            self.sid = sid
            self.years = years
            return sid, years
    
    def __str__(self):
        return self.title

    async def get_episodes(self):
        
        sid, years = await self.get_sid_year()
        eps = []
        for year in years:
            page = 1
            while True:
                l = []
                res = await web.get("https://www.alphatv.gr/ajax/Isobar.AlphaTv.Components.Shows.Show.episodeslist", params={
                    "Key": year,
                    "Page": page,
                    "PageSize": "12",
                    "ShowId": sid  
                })
                if res.status == 200:
                    root = PyQuery(await res.text()).find("a[class='openVideoPopUp']")
                    for el in root:
                        l.append(Episode(el, self, year))
                eps.extend(l)
                if not l:
                    break
                page += 1
        return eps

async def get_shows():
    res = await web.get("https://www.alphatv.gr/ajax/Isobar.AlphaTv.Components.Shows.Show.list?&Page=1&PageSize=1000&ShowType=1")
    l = []
    if res.status == 200:
        root = PyQuery(await res.text()).find("a")
        for el in root:
            l.append(Show(el))
    return l