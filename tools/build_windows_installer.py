"""Build the single-file Windows installer for StudyFlow."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
FRONTEND = ROOT / "frontend"
PYTHON = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
WEBVIEW2_BOOTSTRAPPER = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
ISCC_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
]


def run(command: list[str], cwd: Path) -> None:
    if os.name == "nt":
        subprocess.run(subprocess.list2cmdline(command), cwd=cwd, shell=True, check=True)
    else:
        subprocess.run(command, cwd=cwd, check=True)


def download_webview2_bootstrapper(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        WEBVIEW2_BOOTSTRAPPER,
        headers={"User-Agent": "StudyFlow installer builder"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            with destination.open("wb") as installer:
                shutil.copyfileobj(response, installer)
        if destination.stat().st_size < 100_000:
            raise ValueError("O arquivo baixado não parece ser o instalador do WebView2.")
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise SystemExit(f"Não foi possível baixar o instalador oficial do WebView2: {exc}") from exc


def main() -> None:
    version = sys.argv[1].removeprefix("v") if len(sys.argv) > 1 else "1.0.0"
    if not PYTHON.is_file():
        raise SystemExit("Ambiente backend/.venv não encontrado. Consulte as instruções no README.")

    pnpm = shutil.which("pnpm.cmd") or shutil.which("pnpm")
    corepack = shutil.which("corepack.cmd") or shutil.which("corepack")
    if pnpm:
        pnpm_command = [pnpm]
    elif corepack:
        pnpm_command = [corepack, "pnpm"]
    else:
        raise SystemExit("pnpm/Corepack não encontrado no computador de build.")
    if not (FRONTEND / "node_modules").is_dir():
        raise SystemExit("Dependências do frontend ausentes. Execute pnpm install dentro de frontend.")

    iscc = next((candidate for candidate in ISCC_CANDIDATES if candidate.is_file()), None)
    iscc = str(iscc) if iscc else shutil.which("ISCC.exe")
    if not iscc:
        raise SystemExit("Inno Setup 6 não encontrado. Ele é necessário apenas para gerar o instalador.")

    run(pnpm_command + ["exec", "tsc", "-b"], FRONTEND)
    run(pnpm_command + ["exec", "vite", "build", "--configLoader", "native"], FRONTEND)
    run([str(PYTHON), "-m", "pip", "install", "-r", str(TOOLS / "requirements-packaging.txt")], ROOT)
    run([str(PYTHON), "-m", "PyInstaller", "--noconfirm", "--clean", str(TOOLS / "StudyFlow.spec")], ROOT)
    download_webview2_bootstrapper(ROOT / "dist" / "MicrosoftEdgeWebView2Setup.exe")
    run([str(iscc), f"/DAppVersion={version}", str(TOOLS / "StudyFlow.iss")], ROOT)

    print(f"Instalador criado: {ROOT / 'dist-installer' / 'StudyFlow-Setup.exe'}")


if __name__ == "__main__":
    main()
