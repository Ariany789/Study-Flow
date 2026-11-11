import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=0.5):
            return True
    except (OSError, urllib.error.URLError):
        return False


def show_error(message: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, "StudyFlow", 0x10)
    except Exception:
        print(message, file=sys.stderr)


def wait_for(url: str, attempts: int = 60) -> bool:
    for _ in range(attempts):
        if ready(url):
            return True
        time.sleep(0.5)
    return False


def main() -> None:
    package_manager = shutil.which("pnpm.cmd") or shutil.which("pnpm")
    corepack = shutil.which("corepack.cmd") or shutil.which("corepack")
    if package_manager:
        package_command = [package_manager]
    elif corepack:
        package_command = [corepack, "pnpm"]
    else:
        show_error("Node.js e Corepack/pnpm são necessários para iniciar a interface. Instale o Node.js e tente novamente.")
        return

    dev_command = package_command + ["run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"]
    use_shell = sys.platform == "win32" and package_command[0].lower().endswith((".cmd", ".bat"))

    if not ready("http://127.0.0.1:8000/health"):
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--app-dir", str(BACKEND)],
            cwd=ROOT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not wait_for("http://127.0.0.1:8000/health"):
            show_error("A API do StudyFlow não iniciou. Confira as dependências do backend e tente novamente.")
            return

    if not ready("http://127.0.0.1:5173"):
        if not (FRONTEND / "node_modules").exists():
            install_command = package_command + ["install", "--frozen-lockfile"]
            install = subprocess.run(
                subprocess.list2cmdline(install_command) if use_shell else install_command,
                cwd=FRONTEND, capture_output=True, text=True, shell=use_shell,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if install.returncode:
                show_error("Não foi possível instalar as dependências do frontend.\n\n" + install.stderr[-1500:])
                return
        subprocess.Popen(
            subprocess.list2cmdline(dev_command) if use_shell else dev_command,
            cwd=FRONTEND,
            shell=use_shell,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not wait_for("http://127.0.0.1:5173"):
            show_error("A interface do StudyFlow não iniciou. Confira se a porta 5173 está disponível.")
            return

    webbrowser.open("http://localhost:5173")


if __name__ == "__main__":
    main()
