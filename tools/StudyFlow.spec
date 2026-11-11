# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PIL import Image, ImageDraw
from PyInstaller.utils.hooks import collect_all


tools_dir = Path(SPECPATH)
project_root = tools_dir.parent
icon_path = tools_dir / "studyflow.ico"

icon = Image.new("RGBA", (256, 256), (21, 28, 48, 255))
draw = ImageDraw.Draw(icon)
draw.rounded_rectangle((12, 12, 244, 244), radius=62, fill=(82, 103, 223, 255))
draw.polygon([(128, 40), (146, 105), (211, 128), (146, 150), (128, 216), (107, 150), (43, 128), (107, 105)], fill=(255, 255, 255, 255))
icon.save(icon_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

datas = [(str(project_root / "frontend" / "dist"), "frontend/dist")]
binaries = []
hiddenimports = [
    "app.main",
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "email_validator",
    "multipart",
    "webview",
]

for package in (
    "fastapi",
    "starlette",
    "uvicorn",
    "sqlalchemy",
    "pydantic",
    "pydantic_settings",
    "jose",
    "cryptography",
    "passlib",
    "email_validator",
    "multipart",
    "webview",
    "PIL",
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

a = Analysis(
    [str(tools_dir / "desktop_app.py")],
    pathex=[str(project_root / "backend")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "httpx", "tkinter"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="StudyFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
)
