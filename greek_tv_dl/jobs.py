from asyncio import get_event_loop, run_coroutine_threadsafe, Event
from appJar import gui
from aiohttp import ClientSession, ClientConnectorError
from os import getenv

DAEMON = getenv("DAEMON_ADDR", "http://localhost:25560")

loop = get_event_loop()
app = gui("Greek TV Downloader", "350x600", handleArgs=False)
web = ClientSession()
ev = Event()
ev.clear()
job_ids = []

async def update(_=None):
    try:
        res = await web.get(DAEMON+"/get_jobs")
    except ClientConnectorError:
        app.queueFunction(app.errorBox, "daemon_not_running", "daemon_not_running")
        app.stop()
        return
    if res.status == 200:
        res = await res.json()
        populate_list(res)
        print()

def cancel(button):
    job_id = button.split("cancel")[1]
    async def coro():
        res = await web.get(DAEMON+"/cancel_job", params={
            "job_id": job_id
        })
        if res.status == 200:
            app.queueFunction(app.infoBox, "Επιτυχία", "Η εργασία {} ακυρώθηκε!".format(job_id))
            await update()
            if job_id in job_ids:
                job_ids.remove(job_id)
        else:
            app.queueFunction(app.errorBox, "Κάτι πήγε στραβά", await res.text())
    run_coroutine_threadsafe(coro(), loop)


def populate_list(ids):
    global job_ids
    ev.clear()
    app.openScrollPane( "PANE")
    for i in job_ids:
        if i not in ids:
            app.removeLabelFrame(str(i))
    for i in [i for i in ids if not i in job_ids]:
        app.startLabelFrame(i)
        app.addLabel( "nowdl{}".format(i), "Παρακαλώ περιμένετε")
        app.addMeter( "meter{}".format(i))
        app.setMeterFill( "meter{}".format(i), "blue")
        app.addNamedButton( "Ακύρωση", "cancel{}".format(i) , cancel)
        app.stopLabelFrame()
    app.stopScrollPane()
    job_ids = ids
    ev.set()

def run():
    app.startScrollPane("PANE")
    app.stopScrollPane()
    async def coro():
        try:
            res = await web.get(DAEMON+"/get_jobs")
        except ClientConnectorError:
            app.queueFunction(app.errorBox, "daemon_not_running", "daemon_not_running")
            app.stop()
        if res.status == 200:
            res = await res.json()
            if not res:
                app.infoBox("", "Δεν τρέχουν εργασίες αυτή τη στιγμή.")
            populate_list(res)
        ws = await web.ws_connect(DAEMON+"/socket")
        while not ws.closed:
            message = await ws.receive_json()
            await ev.wait()
            for id, data in message.items():
                if id not in job_ids:
                    await update()
                try:
                    app.queueFunction(app.setMeter, "meter{}".format(id),
                    (100*data['current'])//data['total'],
                    text="{}/{}".format(data['current'], data['total']))
                    app.queueFunction(app.setLabel, "nowdl{}".format(id), data['downloading']['title'])
                except:
                    continue
    run_coroutine_threadsafe(coro(), loop)
    app.thread(loop.run_forever)
    app.go()

if __name__ == '__main__':
    run()