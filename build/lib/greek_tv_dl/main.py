# pylint: disable=F0401
from greek_tv_dl._version import __VERSION__

from argparse import ArgumentParser
from os import getenv, name, path, makedirs
from asyncio import get_event_loop
from aiohttp import ClientSession
from subprocess import check_output, Popen
from getpass import getuser
from json import load, dump

def daemon_running():
    try:
        res = get_event_loop().run_until_complete(ClientSession().get("http://{}:{}/info".format(host, port)))
    except:
        return
    if res.status == 200 and 'GreekTvDl-Version' in res.headers and res.headers['GreekTvDl-Version'] == __VERSION__:
        return True

def config_gen():
    user = getuser()
    BASE_CONFIG = {
        "save_dir": "C:\\Users\\{}\\Videos".format(user) if name == 'nt' else "/home/{}/Videos".format(user),
        "daemon_host": "0.0.0.0",
        "daemon_port": 25560
    }
    if name == 'nt':
        cfg_dir = "C:\\Users\\{}\\AppData\\Roaming\\greek_tv_dl".format(user)
    elif name == 'posix':
        cfg_dir = "/home/{}/.config/greek_tv_dl".format(user)
    else:
        print("No supported system found")
        exit(1)
    try:
        cfg = load(path.join(cfg_dir, "config.json"))
    except:
        cfg = BASE_CONFIG
        makedirs(cfg_dir, exist_ok=True)
        with open(path.join(cfg_dir, "config.json"), "w+") as f:
            dump(BASE_CONFIG, f)
    return cfg

host = getenv("GREEK_TV_DL_DAEMON_HOST", config_gen()['daemon_host'] if 'daemon_host' in config_gen() else "0.0.0.0")
port = int(getenv("GREEK_TV_DL_DAEMON_PORT", str(config_gen()['daemon_port'] if 'daemon_port' in config_gen() else 25560)))

parser = ArgumentParser()
parser.add_argument("--daemon", help="Run the daemon", action="store_true")
parser.add_argument("--jobs", help="Open jobs window", action="store_true")
parser.add_argument("--gui", help="Open gui without checking for a running daemon", action="store_true")
parser.add_argument("--port", type=int, help="Port to run the server on if running with --daemon else port to connect to")
parser.add_argument("--host", type=str, help="Address to run the server on if running with --daemon else address to connect to")
parser.add_argument("--https", help="Use an https:// prefix to connect to the server. Useful with remote daemons", action="store_true")
parser.add_argument("--headless", help="Disables systray icon for daemon", action="store_true")

options = parser.parse_args()

def main():
    if options.daemon:
        from greek_tv_dl.daemon import run
        run(host=options.host or host, port=options.port or port, systray=not bool(options.headless))
        return
    elif options.jobs:
        from greek_tv_dl import jobs as gui
    else:
        from greek_tv_dl import gui
    gui.DAEMON = "http{}://{}:{}".format("s" if options.https else "", options.host or "localhost", options.port or port)
    if not options.gui and not daemon_running():
        Popen("greek-tv-dl --daemon", shell=True)
    gui.run()

if __name__ == '__main__':
    main()