# pylint: disable=F0401

from appJar import gui
from appJar.appjar import ItemLookupError
from asyncio import get_event_loop, sleep

loop = get_event_loop()
app = gui("Greek TV Downloader", "600x300")

shows = [None] #TODO: Make this prettier
def get_shows():
    return shows[0]
def set_shows(s):
    shows[0] = s

async def _(): #TODO: Fix so it doesn't need this
    while True:
        await sleep(1)
loop.create_task(_())

def get_channel():
    channel = app.getOptionBox("Κανάλι")
    if channel == "ANT1":
        from channels import ant1 as provider
    elif channel == "Alpha":
        from channels import alpha as provider
    elif channel == "Star":
        from channels import star as provider
    elif channel == "Open":
        from channels import opentv as provider
    try:
        app.addLabel("loading", "Παρακαλώ περιμένετε...")
    except Exception:
        return
    def _(task):
        app.queueFunction(app.removeLabel, "loading")
        set_shows(task.result())
        app.queueFunction(app.updateListBox, "series", get_shows())
    loop.create_task(provider.get_shows()).add_done_callback(_)

def get_show():
    async def coro():
        show = app.getListBox("series")
        if show:
            show = next(s for s in get_shows() if s.title == show[0])
            app.queueFunction(app.addLabel, "loading", "Παρακαλώ περιμένετε...")
            episodes = await show.get_episodes()
            if not episodes:
                app.queueFunction(app.removeLabel, "loading")
                app.queueFunction(app.warningBox, show, "Δεν υπάρχουν επεισόδια προς λήψη.")
                return
            app.queueFunction(app.openSubWindow, "eps")
            app.queueFunction(app.setTitle, show.title)
            app.queueFunction(app.replaceAllTableRows, "episodes", [[i] for i in episodes], deleteHeader=False)
            app.queueFunction(app.removeButton, "Λήψη")
            app.queueFunction(app.addButton, "Λήψη", lambda: download(show, episodes))
            app.queueFunction(app.stopSubWindow)
            app.queueFunction(app.removeLabel, "loading")
            app.queueFunction(app.showSubWindow, "eps")
    loop.create_task(coro())

def download(show, episodes):
    indexes = [int(i.split("-")[0]) for i in app.getTableSelectedCells("episodes")]
    eps = [episodes[i] for i in indexes]
    async def coro():
        app.queueFunction(app.startSubWindow, "dl", title=show, modal=True)
        app.queueFunction(app.addLabel, "title", show)
        app.queueFunction(app.addLabel, "progress", "")
        app.queueFunction(app.showSubWindow, "dl")
        app.queueFunction(app.stopSubWindow)
        for i,v in enumerate(eps):
            app.queueFunction(app.openSubWindow, "dl")
            app.queueFunction(app.setLabel, "progress" ,"Γίνεται λήψη: {}\n{}/{}".format(v, i+1, len(eps)))
            app.queueFunction(app.stopSubWindow)
            await v.download()
        app.queueFunction(app.destroySubWindow, "dl")
        app.queueFunction(app.infoBox, show, "Η λήψη ολοκληρώθηκε")
        

    loop.create_task(coro())

def handle_menu(option):
    if option == "Κονσόλα":
        import code
        code.interact(local=locals())
    elif option == "Ρυθμίσεις":
        pass
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

Made by marios8543
Enjoy ⁽⁽ଘ( ˊᵕˋ )ଓ⁾⁾
        """, parent=None)

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
app.addMenuList("Αρχείο", ["Ρυθμίσεις", "-", "Κονσόλα", "-", "Έξοδος"], handle_menu)
app.addMenuList("Βοήθεια", ["Εγχειρίδιο χρήσης", "Έλεγχος για ενημερώσεις", "Πληροφορίες"], handle_menu)

app.startSubWindow("eps", title="", modal=True)
app.addTable("episodes", [["Επεισόδια"]])
app.addLabel("help", "Επιλέξτε όσα θέλετε να κατεβάσετε και πατήστε")
app.addButton("Λήψη", lambda _: None)
app.stopSubWindow()

def run():
    app.thread(loop.run_forever)
    app.go()

if __name__ == '__main__':
    run()