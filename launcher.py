import os, socket, threading, time
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sawanih.settings")

import django
django.setup()

from django.core.management import call_command
from waitress import serve
from sawanih.wsgi import application
import webview   # pip install pywebview

def free_port(start=8765):
    for p in range(start, start + 50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p

if __name__ == "__main__":
    call_command("migrate", interactive=False)      # creates/updates the DB
    port = free_port()
    threading.Thread(
        target=serve, args=(application,),
        kwargs={"host": "127.0.0.1", "port": port}, daemon=True,
    ).start()
    time.sleep(1.5)
    webview.create_window("سوانح", f"http://127.0.0.1:{port}/", width=1280, height=800)
    webview.start()      # closing the window ends the program and the server