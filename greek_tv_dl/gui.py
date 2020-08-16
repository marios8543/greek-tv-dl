# pylint: disable=F0401
from greek_tv_dl._version import __VERSION__

from appJar import gui
from asyncio import get_event_loop, sleep, Lock, run_coroutine_threadsafe
from aiohttp import ClientSession, ClientConnectorError
from os import getenv, name

loop = get_event_loop()
app = gui("Greek TV Downloader", "600x300", handleArgs=False)
web = ClientSession()
DAEMON = getenv("DAEMON_ADDR", "http://localhost:25560")
shows = {}
_lock = Lock()

async def lock():
    if _lock.locked():
        return
    await _lock.acquire()
    try:
        app.queueFunction(app.addLabel, "loading", "Παρακαλώ περιμένετε...")
    except:
        pass
    return 1

def unlock():
    _lock.release()
    app.queueFunction(app.removeLabel, "loading")

def get_channel():
    channel = app.getOptionBox("Κανάλι")
    async def coro():
        if not await lock():
            return
        try:
            res = await web.get(DAEMON+"/get_shows", params={"channel": channel})
        except ClientConnectorError:
            app.queueFunction(app.errorBox, "daemon_not_running", "daemon_not_running")
        unlock()
        if res.status == 200:
            res = await res.json()
            shows.clear()
            for i in res:
                shows[i['title']] = i
            app.queueFunction(app.updateListBox, "series", [i["title"] for i in res])
        else:
            app.queueFunction(app.errorBox, res.status, "Κάτι πήγε στραβά")
    run_coroutine_threadsafe(coro(), loop)

def get_show():
    async def coro():
        show = app.getListBox("series")
        channel = app.getOptionBox("Κανάλι")
        if show:
            show = shows[show[0]]
            if not await lock():
                return
            res = await web.get(DAEMON+'/get_episodes', params={"channel": channel, "show_id": show['id']})
            if res.status == 200:
                episodes = await res.json()
                if not episodes:
                    unlock()
                    app.queueFunction(app.warningBox, show, "Δεν υπάρχουν επεισόδια προς λήψη.")
                    return
                app.queueFunction(app.openSubWindow, "eps")
                app.queueFunction(app.setTitle, show['title'])
                app.queueFunction(app.replaceAllTableRows, "episodes", [[i['title']] for i in episodes], deleteHeader=False)
                app.queueFunction(app.removeButton, "Λήψη")
                app.queueFunction(app.addButton, "Λήψη", lambda: download(show, episodes))
                app.queueFunction(app.stopSubWindow)
                app.queueFunction(app.showSubWindow, "eps")
                unlock()
            else:
                app.queueFunction(app.errorBox, res.status, "Κάτι πήγε στραβά")
                unlock()
    run_coroutine_threadsafe(coro(), loop)

def download(show, episodes):
    indexes = [int(i.split("-")[0]) for i in app.getTableSelectedCells("episodes")]
    ids = [episodes[i]['id'] for i in indexes]
    run_coroutine_threadsafe(web.get(DAEMON+"/add_job", params={"episode_ids":",".join(ids)}), loop).add_done_callback(lambda task: 
        (app.infoBox(show['title'], "Προστέθηκε στη λίστα εργασιών!"),
        app.hideSubWindow("eps")
        ) if task.result().status == 200 else 
        app.errorBox(show['title'], "Κάτι πήγε στραβά")
    )

def handle_menu(option):
    if option == "Κονσόλα":
        import code
        code.interact(local=locals())
    if option == "Εργασίες":
        from subprocess import Popen
        Popen('START /B "" greek-tv-dl --jobs' if name=='nt' else "greek-tv-dl --jobs", shell=True)
    elif option == "Φάκελος αποθήκευσης":
        directory = app.directoryBox(title="Φάκελος αποθήκευσης")
        run_coroutine_threadsafe(web.get(DAEMON+'/set_save_dir', params={"dir":directory}), loop)
        app.infoBox("Επιτυχία", "Ο φάκελος αποθήκευσης ορίστηκε.")
    elif option == "Έξοδος":
        app.stop()
    elif option == "Εγχειρίδιο χρήσης":
        pass
    elif option == "Έλεγχος για ενημερώσεις":
        pass
    elif option == "Πληροφορίες":
        app.infoBox("Greek TV Downloader", """
Κατεβαστήρι σειρών και λοιπών σκουπιδιών από τα έγκατα των ιστοσελίδων γνωστών ελληνικών καναλιών.
Όπως και τα περισσότερα πράγματα σε αυτή τη χώρα, δεν θα λειτουργεί απαραίτητα πάντα και μάλλον είναι παράνομο.

Made by funny yellow dog#9110
Enjoy ⁽⁽ଘ( ˊᵕˋ )ଓ⁾⁾
        """, parent=None)

def run():
    app.addLabelOptionBox("Κανάλι", [
        "Επιλέξτε κανάλι",
        "ANT1",
        "Alpha",
        "Star",
        "Open"
    ])
    app.setOptionBoxChangeFunction("Κανάλι", get_channel)
    app.addListBox("series", [])
    app.setListBoxChangeFunction("series", get_show)
    app.addMenuList("Αρχείο", ["Φάκελος αποθήκευσης", "Εργασίες", "-", "Έξοδος"], handle_menu)
    app.addMenuList("Βοήθεια", ["Εγχειρίδιο χρήσης", "Έλεγχος για ενημερώσεις", "Πληροφορίες"], handle_menu)

    app.startSubWindow("eps", title="", modal=True)
    app.addTable("episodes", [["Επεισόδια"]])
    app.addLabel("help", "Επιλέξτε όσα θέλετε να κατεβάσετε και πατήστε")
    app.addButton("Λήψη", lambda _: None)
    app.stopSubWindow()
    app.thread(loop.run_forever)
    app.go()

if __name__ == '__main__':
    run()