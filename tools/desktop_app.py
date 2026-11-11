"""Launch the bundled StudyFlow API and web app as a Windows desktop app."""
from __future__ import annotations

import ctypes
import os
import secrets
import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "StudyFlow"


def show_error(message: str) -> None:
    ctypes.windll.user32.MessageBoxW(None, message, "StudyFlow", 0x10)


def set_runtime_environment() -> Path:
    data = data_root()
    data.mkdir(parents=True, exist_ok=True)
    secret_path = data / "jwt-secret"
    try:
        with secret_path.open("x", encoding="ascii") as secret_file:
            secret_file.write(secrets.token_hex(48))
    except FileExistsError:
        pass

    database_path = (data / "studyflow.db").as_posix()
    os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
    os.environ["JWT_SECRET"] = secret_path.read_text(encoding="ascii").strip()
    os.environ["ENVIRONMENT"] = "production"
    return data


def acquire_single_instance(data: Path) -> int | None:
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "Local\\StudyFlow.Desktop")
    if ctypes.windll.kernel32.GetLastError() == 183:
        url_path = data / "instance-url"
        try:
            url = url_path.read_text(encoding="ascii").strip()
            if url:
                webbrowser.open(url)
        except OSError:
            pass
        return None
    return mutex


def available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def make_tray_image():
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (64, 64), (21, 28, 48, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((4, 4, 60, 60), radius=16, fill=(82, 103, 223, 255))
    draw.polygon([(32, 11), (36, 26), (51, 32), (36, 36), (32, 52), (28, 36), (13, 32), (28, 26)], fill=(255, 255, 255, 255))
    return image


def run() -> None:
    import pystray
    import uvicorn

    data = set_runtime_environment()
    mutex = acquire_single_instance(data)
    if mutex is None:
        return

    if not getattr(sys, "frozen", False):
        sys.path.insert(0, str(resource_root() / "backend"))
    from app.main import app

    port = available_port()
    url = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="critical",
        access_log=False,
    ))
    server_thread = threading.Thread(target=server.run, name="studyflow-api", daemon=True)
    server_thread.start()

    for _ in range(100):
        if server.started:
            break
        if not server_thread.is_alive():
            raise RuntimeError("A API do StudyFlow não iniciou.")
        time.sleep(0.1)
    else:
        server.should_exit = True
        raise RuntimeError("A API do StudyFlow demorou demais para iniciar.")

    (data / "instance-url").write_text(url, encoding="ascii")

    def exit_app(icon, _item):
        server.should_exit = True
        icon.stop()

    tray = pystray.Icon(
        "StudyFlow",
        make_tray_image(),
        "StudyFlow",
        menu=pystray.Menu(
            pystray.MenuItem("Abrir StudyFlow", lambda _icon, _item: webbrowser.open(url), default=True),
            pystray.MenuItem("Sair", exit_app),
        ),
    )
    tray.run_detached()
    webbrowser.open(url)
    try:
        server_thread.join()
    finally:
        tray.stop()
        try:
            (data / "instance-url").unlink()
        except FileNotFoundError:
            pass
        ctypes.windll.kernel32.ReleaseMutex(mutex)
        ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        try:
            log_path = data_root() / "startup-error.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(f"{exc}\n\n{traceback.format_exc()}", encoding="utf-8")
        except OSError:
            pass
        show_error(f"O StudyFlow não conseguiu iniciar.\n\n{exc}")
