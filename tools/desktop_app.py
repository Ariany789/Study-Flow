"""Launch the bundled StudyFlow API and web app as a Windows desktop app."""
from __future__ import annotations

import ctypes
import os
import secrets
import sys
import threading
import time
import traceback
from pathlib import Path


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "StudyFlow"


def show_error(message: str) -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.MessageBoxW(None, message, "StudyFlow", 0x10)


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


def acquire_single_instance() -> int | None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    mutex = kernel32.CreateMutexW(None, True, "Local\\StudyFlow.Desktop")
    if ctypes.get_last_error() == 183:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        user32.FindWindowW.restype = ctypes.c_void_p
        user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        window = user32.FindWindowW(None, "StudyFlow")
        if window:
            user32.ShowWindow(window, 9)  # SW_RESTORE
            user32.SetForegroundWindow(window)
        else:
            show_error("O StudyFlow já está aberto.")
        return None
    return mutex


APP_PORT = 43187


def run() -> None:
    import uvicorn
    import webview

    data = set_runtime_environment()
    mutex = acquire_single_instance()
    if mutex is None:
        return

    if not getattr(sys, "frozen", False):
        sys.path.insert(0, str(resource_root() / "backend"))
    from app.main import app

    # Keep one stable origin so the embedded webview can retain the login token
    # in localStorage between app launches.
    url = f"http://127.0.0.1:{APP_PORT}"
    server = uvicorn.Server(uvicorn.Config(
        app,
        host="127.0.0.1",
        port=APP_PORT,
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

    webview.create_window(
        "StudyFlow",
        url,
        width=1280,
        height=860,
        min_size=(900, 620),
        background_color="#151c30",
    )
    try:
        webview.start(
            gui="edgechromium",
            private_mode=False,
            storage_path=str(data / "webview"),
        )
    finally:
        server.should_exit = True
        server_thread.join(timeout=10)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.ReleaseMutex.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.ReleaseMutex(mutex)
        kernel32.CloseHandle(mutex)


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
        detail = str(exc)
        if "webview2" in detail.lower() or "edgechromium" in detail.lower():
            message = (
                "O Microsoft Edge WebView2 Runtime não está disponível neste computador. "
                "Instale o WebView2 Runtime e abra o StudyFlow novamente.\n\n"
                f"Detalhes: {detail}"
            )
        else:
            message = f"O StudyFlow não conseguiu iniciar.\n\n{detail}"
        show_error(message)
